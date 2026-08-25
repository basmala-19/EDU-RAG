from __future__ import annotations

import math
import re
from functools import lru_cache
import requests
from src.infrastructure.config import get_settings
from src.infrastructure.ar_text import normalize_ar_token


@lru_cache(maxsize=4)
def _get_reranker(model_name: str, device: str):
    """Load the CrossEncoder once per (model, device) and reuse it across requests.

    Previously this was instantiated on every rerank_and_dedup() call, which
    reloads the full bge-reranker-v2-m3 weights from disk/cache on every single
    query — the single biggest avoidable latency cost in the retrieval path.
    """
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device)

_AR_STOP = {"من","في","على","عن","إلى","الى","هو","هي","ما","ماذا","هل","و","أو","أن","إن","الذي","التي","the","a","an","of","to","in","on","is","are","what","how","and","or"}

def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9][a-z0-9_./+\-]*|[\u0600-\u06FF]+", (text or "").casefold())
    out=set()
    for t in raw:
        t=re.sub(r"[\u064B-\u065F\u0670]", "", t).replace("ـ", "")
        t=normalize_ar_token(t)
        if len(t)>1 and t not in _AR_STOP:
            out.add(t)
    return out

def _norm_rrf(rrf: float, weight_sum: float) -> float:
    anchor=max(weight_sum/61.0,1e-9)
    return min(1.0,rrf/anchor)

def _rerank_with_openrouter(query: str, candidates: list[dict], settings) -> None:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required when RERANKER_BACKEND=openrouter")
    response = requests.post(
        f"{settings.openrouter_base_url.rstrip('/')}/rerank",
        headers={"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"},
        json={"model": settings.reranker_model, "query": query, "documents": [str(item.get("document", "")) for item in candidates], "top_n": len(candidates)},
        timeout=settings.openrouter_timeout,
    )
    response.raise_for_status()
    rows = response.json().get("results") or []
    for item in candidates:
        item["reranker_score"] = 0.0
    for row in rows:
        index = int(row["index"])
        if 0 <= index < len(candidates):
            candidates[index]["reranker_score"] = min(1.0, max(0.0, float(row["relevance_score"])))

def rerank_and_dedup(results:list[dict], top_k:int, query:str="") -> list[dict]:
    settings=get_settings(); q=_tokens(query); qtext=query.casefold()
    weights={"semantic":settings.semantic_weight,"question":settings.question_weight,"keyword":settings.keyword_weight}
    channels={"semantic":[],"question":[],"keyword":[]}; candidates={}
    for item in results:
        cid=str(item["id"]); candidates.setdefault(cid,dict(item))
        if item.get("question_match"):
            candidates[cid]["question_match"]=True; candidates[cid]["question_distance"]=min(float(candidates[cid].get("question_distance",1.0)),float(item.get("question_distance",item.get("distance",1.0))))
        if item.get("keyword_match"):
            candidates[cid]["keyword_match"]=True; candidates[cid]["keyword_score"]=max(float(candidates[cid].get("keyword_score",0.0)),float(item.get("keyword_score",0.0)))
    for item in candidates.values():
        channels["semantic"].append(item)
        if item.get("question_match"): channels["question"].append(item)
        if item.get("keyword_match"): channels["keyword"].append(item)
    channels["semantic"].sort(key=lambda x:float(x.get("distance",1.0)))
    channels["question"].sort(key=lambda x:float(x.get("question_distance",1.0)))
    channels["keyword"].sort(key=lambda x:float(x.get("keyword_score",0.0)),reverse=True)
    ranks={n:{str(x["id"]):i+1 for i,x in enumerate(rows)} for n,rows in channels.items()}
    weight_sum=sum(weights.values())
    definition_q=bool(re.search(r"(?:ما هو|ما هي|ما المقصود|تعريف|what is|define)",qtext,re.I))
    ranked=[]; seen=set()
    for cid,item in candidates.items():
        doc=re.sub(r"\s+"," ",str(item.get("document","")).casefold()).strip(); meta=item.get("metadata") or {}
        dedupe_key=doc[:500]
        if dedupe_key in seen: continue
        seen.add(dedupe_key)
        rrf=0.0; contributed=[]
        for n,rm in ranks.items():
            rank=rm.get(cid)
            if rank:
                rrf += weights[n]/(60+rank); contributed.append(n)
        overlap=len(q&_tokens(doc))/max(len(q),1)
        h_overlap=len(q&_tokens(str(meta.get("heading") or "")))/max(len(q),1)
        exact=1.0 if q and q.issubset(_tokens(doc)) else 0.0
        ctype=1.0 if meta.get("content_type") in {"definition","paragraph","example","table"} else 0.5
        direct=(0.24*exact+0.18*overlap+0.10*h_overlap) if definition_q else (0.14*overlap+0.08*h_overlap)
        score=0.48*_norm_rrf(rrf,weight_sum)+0.42*direct+0.10*ctype
        ranked.append({**item,"score":float(min(1.0,score)),"rrf_score":float(_norm_rrf(rrf,weight_sum)),"lexical_overlap":float(overlap),"heading_overlap":float(h_overlap),"retrieval_channels":contributed})
    ranked.sort(key=lambda x:x["score"],reverse=True)
    candidates=ranked[:max(top_k,settings.reranker_candidates)]
    if settings.reranker_enabled and candidates:
        try:
            if settings.reranker_backend.casefold() == "openrouter":
                _rerank_with_openrouter(query, candidates, settings)
            elif settings.reranker_backend.casefold() == "local":
                ce=_get_reranker(settings.reranker_model,settings.embedding_device)
                vals=ce.predict([(query,str(x.get("document",""))) for x in candidates],show_progress_bar=False)
                for x,v in zip(candidates,vals):
                    v=float(v)
                    x["reranker_score"]=min(1.0,max(0.0,v))
            else:
                raise RuntimeError("RERANKER_BACKEND must be 'openrouter' or 'local'")
                # BAAI/bge-reranker-v2-m3 already returns a calibrated [0,1] relevance
                # probability from CrossEncoder.predict() (its own activation is applied
                # internally) — applying sigmoid() again here on top of that squashed every
                # score toward ~0.5 regardless of true relevance (e.g. a genuinely irrelevant
                # doc at v≈0.0002 became 0.50005 instead of staying ~0), which made the
                # pre-generation "catastrophic irrelevance" gate unable to tell garbage
                # retrieval from a real answer. Just clip, don't re-sigmoid.
        except Exception as exc:
            for x in candidates: x["reranker_score"]=float(x["score"]); x["reranker_error"]=f"{type(exc).__name__}: {exc}"
    for x in candidates:
        rer=float(x.get("reranker_score",x["score"]))
        x["retrieval_confidence"]=float(min(1.0,max(0.0,0.60*rer+0.25*x["lexical_overlap"]+0.15*min(1.0,len(x["retrieval_channels"])/2))))
    candidates.sort(key=lambda x:(x.get("reranker_score",0),x["retrieval_confidence"],x["score"]),reverse=True)
    return candidates[:top_k]

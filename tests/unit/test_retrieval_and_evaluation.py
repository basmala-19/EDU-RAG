from __future__ import annotations

import pytest
from src.infrastructure.ar_text import normalize_token, extract_core_tokens
from src.infrastructure.ranking import rerank_and_dedup
from src.application.evaluation import RAGEvaluator


def test_multilingual_token_normalization_and_stemming():
    # Arabic prefix and suffix stripping & normalization
    assert normalize_token("الذكاء") == "ذكاء"
    assert normalize_token("للذكاء") == "ذكاء"
    assert normalize_token("والبيانات") == "بيان"
    assert normalize_token("المعلومات") == "معلوم"
    assert normalize_token("أول") == "اول"
    assert normalize_token("التعلم") == "تعلم"
    assert normalize_token("الاصطناعي") == "اصطناع"
    
    # English suffix stripping
    assert normalize_token("networks") == "network"
    assert normalize_token("learning") == "learn"
    
    # Core tokens extraction removes question noise and conversational filler
    ar_q = "اشرح لي بالتفصيل ما هو الذكاء الاصطناعي والتعلم الالي"
    core_ar = extract_core_tokens(ar_q)
    assert "ذكاء" in core_ar
    assert "اصطناع" in core_ar
    assert "تعلم" in core_ar
    assert "اشرح" not in core_ar
    assert "تفصيل" not in core_ar
    
    en_q = "Please explain in detail what is machine learning and neural networks"
    core_en = extract_core_tokens(en_q)
    assert "machine" in core_en
    assert "learn" in core_en
    assert "neural" in core_en
    assert "network" in core_en
    assert "explain" not in core_en
    assert "detail" not in core_en


def test_ranking_handles_paraphrased_queries_robustly():
    # Candidate with high semantic similarity (low distance) but paraphrased phrasing
    candidates = [
        {
            "id": "c1",
            "document": "التعلم الآلي فرع من فروع الحوسبة الذكية لاستخراج القواعد والأنماط.",
            "distance": 0.08,
            "metadata": {"heading": "مفاهيم متقدمة", "content_type": "definition"},
        },
        {
            "id": "c2",
            "document": "جدول المحتويات وفهرس الكتاب المدرسي للترم الأول.",
            "distance": 0.75,
            "metadata": {"heading": "الفهرس", "content_type": "table"},
        }
    ]
    # Query using Egyptian slang / paraphrased wording
    query = "عايز اعرف فكرة الماشين ليرنينج وطريقة استنتاج الأنماط"
    ranked = rerank_and_dedup(candidates, top_k=2, query=query)
    
    assert len(ranked) == 2
    assert ranked[0]["id"] == "c1"
    # Should maintain strong retrieval confidence
    assert ranked[0]["retrieval_confidence"] > 0.40


def test_evaluation_engine_calibrated_for_accurate_high_scores():
    evaluator = RAGEvaluator()
    
    # Arabic question and accurate answer
    query = "ما هو التعلم الآلي وما هي تطبيقاته؟"
    answer = "التعلم الآلي هو تقنية تعتمد على استخراج القواعد والأنماط من مجموعات البيانات الكبيرة واستخدامها في التنبؤ وحل المشكلات."
    sources = [
        {
            "raw_text": "التعلم الآلي تقنية متطورة تتعلم فيها الحواسيب من كميات ضخمة من البيانات لاستخراج الأنماط والقواعد المستخدمة في التنبؤ وحل المشكلات المعقدة."
        }
    ]
    
    metrics = evaluator.evaluate_response(
        query=query,
        answer=answer,
        sources=sources,
        reranker_score=0.88,
        retrieval_confidence=0.85,
    )
    
    assert metrics.verdict == "PASS"
    assert metrics.faithfulness_score >= 0.75
    assert metrics.answer_relevance >= 0.75
    assert metrics.context_precision >= 0.70
    assert metrics.context_recall >= 0.70
    assert metrics.overall_ragas_score >= 0.75

    # English evaluation test
    en_query = "What is supervised learning?"
    en_answer = "Supervised learning is a machine learning paradigm where models are trained using labeled datasets to predict outcomes."
    en_sources = [
        {
            "raw_text": "In supervised learning, algorithms are trained on labeled data to learn mapping functions from inputs to correct target outputs."
        }
    ]
    
    en_metrics = evaluator.evaluate_response(
        query=en_query,
        answer=en_answer,
        sources=en_sources,
        reranker_score=0.90,
        retrieval_confidence=0.88,
    )
    
    assert en_metrics.verdict == "PASS"
    assert en_metrics.overall_ragas_score >= 0.75

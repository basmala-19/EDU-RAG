`SemanticSplitterNodeParser` is a **semantic boundary detector**. Its job is not to chunk by a fixed number of tokens. Instead, it roughly does this:

```text
Document
   ↓
Split into sentences
   ↓
Create small sentence groups
   ↓
Embed those groups
   ↓
Measure semantic difference between neighboring groups
   ↓
Find unusually large topic shifts
   ↓
Create a new Node at those boundaries
```

So if a document contains:

```text
Neural networks consist of interconnected layers of artificial neurons.
Each connection has an associated weight.
Activation functions introduce non-linearity into the network.
Backpropagation computes gradients used to update the weights.

Decision trees recursively divide data according to feature values.
Information gain is commonly used to select useful splits.
Entropy measures uncertainty in the training data.
```

The goal is to produce something approximately like:

```text
Node 1
------
Neural networks consist of interconnected layers...
Each connection has an associated weight...
Activation functions...
Backpropagation...


Node 2
------
Decision trees recursively divide data...
Information gain...
Entropy...
```

The exact boundaries depend mainly on:

* the embedding model
* `buffer_size`
* `breakpoint_percentile_threshold`

---

# 1. What is a `SemanticSplitterNodeParser`?

The class is:

```python
SemanticSplitterNodeParser
```

It is a **Node Parser** in LlamaIndex.

A Node Parser converts higher-level objects, such as:

```python
Document
```

into smaller LlamaIndex objects:

```text
Document
    ↓
SemanticSplitterNodeParser
    ↓
Node
Node
Node
Node
```

Each resulting `Node` contains a semantically coherent portion of the original document.

Conceptually:

```python
from llama_index.core import Document

document = Document(
    text="Very long document..."
)
```

Then:

```python
nodes = splitter.get_nodes_from_documents(
    [document]
)
```

The result is approximately:

```python
[
    TextNode(
        text="Topic A..."
    ),
    TextNode(
        text="Topic B..."
    ),
    TextNode(
        text="Topic C..."
    )
]
```

---

# 2. How the semantic splitting algorithm works

The important thing to understand is that it does **not** simply embed every sentence and compare:

```text
Sentence 1 ↔ Sentence 2
Sentence 2 ↔ Sentence 3
```

The `buffer_size` parameter allows it to create sentence groups.

Suppose:

```python
buffer_size = 1
```

And you have:

```text
S1
S2
S3
S4
S5
```

The algorithm considers relatively local sentence groupings around each position.

With:

```python
buffer_size = 2
```

the semantic representation used for evaluating a boundary contains more surrounding context.

Conceptually:

```text
Sentence window
────────────────

[S1 + S2]  → embedding A

[S2 + S3]  → embedding B

[S3 + S4]  → embedding C
```

Then it measures how different neighboring embeddings are.

A large semantic difference:

```text
Similarity / semantic continuity

0.95
0.93
0.96
0.94
──────
0.41   ← major semantic change
──────
0.92
0.95
```

suggests a possible chunk boundary.

The splitter then uses `breakpoint_percentile_threshold` to determine which differences are large enough to become boundaries.

---

# 3. `embed_model`

```python
embed_model: BaseEmbedding
```

This is the most important required component.

The semantic splitter needs an embedding model because semantic similarity cannot be determined from raw text alone.

For example:

```text
"Neural networks are composed of neurons."

"Artificial neurons are organized into layers."
```

Although the wording differs, a good embedding model should place them relatively close in vector space.

Conceptually:

```text
Sentence
   ↓
Embedding model
   ↓
[0.12, -0.87, 0.44, ...]
```

Then the splitter can compare vectors.

### Example

With HuggingFace embeddings:

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)
```

Then:

```python
from llama_index.core.node_parser import SemanticSplitterNodeParser

splitter = SemanticSplitterNodeParser(
    embed_model=embed_model
)
```

The embedding model must be a LlamaIndex-compatible `BaseEmbedding` implementation.

---

## Choosing an embedding model

The quality of semantic chunking depends heavily on the embedding model.

A weak embedding model may think:

```text
Neural Networks
```

and:

```text
Neural Network Architecture
```

are not particularly related.

A better model should recognize the relationship.

For academic/technical text, I would generally consider models such as BGE, E5, or other strong retrieval-oriented embedding models.

The key point is:

> The semantic splitter is only as good as the embedding space it uses to detect semantic changes.

---

# 4. `buffer_size`

```python
buffer_size: int = 1
```

The documentation says:

> The number of sentences to group together when evaluating semantic similarity.

This does **not** directly mean:

```text
Each output chunk contains exactly `buffer_size` sentences.
```

That would be ordinary fixed-size chunking.

Instead, `buffer_size` affects the amount of local sentence context used when evaluating semantic continuity.

---

## `buffer_size = 1`

```python
buffer_size=1
```

The semantic comparison is based on individual/local sentences.

Conceptually:

```text
S1
↓
embedding

S2
↓
embedding

S3
↓
embedding
```

This makes the splitter more sensitive to local changes.

### Advantages

* More precise boundaries
* Can detect relatively small topic changes
* Good when paragraphs frequently change subject

### Disadvantages

* A single unusual sentence may cause a false boundary
* Less surrounding context

---

## `buffer_size = 2`

```python
buffer_size=2
```

Now the semantic evaluation includes more surrounding sentences.

Conceptually:

```text
[S1 + S2]
[S2 + S3]
[S3 + S4]
[S4 + S5]
```

This tends to make the semantic representation more stable.

For textbook material, I would generally start experimenting around:

```python
buffer_size=1
```

and:

```python
buffer_size=2
```

rather than immediately using a large value.

---

## Large `buffer_size`

For example:

```python
buffer_size=5
```

Now the algorithm evaluates larger semantic windows.

This may make it less sensitive to small topic shifts.

Conceptually:

```text
Small buffer
────────────

Topic A
Topic A
Topic B ← boundary detected quickly
Topic B


Large buffer
────────────

[Topic A + Topic A + Topic B + Topic B]
```

The transition becomes smoother.

Therefore:

| Buffer size  | Behavior                        |
| ------------ | ------------------------------- |
| `1`          | Most sensitive/local            |
| `2–3`        | More contextual/stable          |
| Large values | Less sensitive to small changes |

For a technical book, I would initially test:

```python
buffer_size=1
```

and:

```python
buffer_size=2
```

then inspect the resulting nodes.

---

# 5. `breakpoint_percentile_threshold`

```python
breakpoint_percentile_threshold: int = 95
```

This parameter determines **how large a semantic difference must be before the splitter creates a new Node**.

This is one of the most important parameters.

Suppose the algorithm calculates semantic dissimilarities between neighboring sentence groups:

```text
0.02
0.04
0.05
0.06
0.08
0.10
0.12
0.15
0.43
0.48
```

The high values represent larger semantic changes.

The splitter uses a percentile threshold to determine which changes are sufficiently unusual.

With:

```python
breakpoint_percentile_threshold=95
```

only differences in roughly the highest 5% are considered breakpoints.

Therefore:

```text
95
│
├── fewer boundaries
├── larger nodes
└── only major topic shifts
```

---

## Lower threshold

For example:

```python
breakpoint_percentile_threshold=80
```

More semantic changes exceed the threshold.

Therefore:

```text
80
│
├── more boundaries
├── smaller nodes
└── more sensitive topic segmentation
```

This is consistent with the documentation:

> The smaller this number is, the more nodes will be generated.

### Rough intuition

| Threshold | Likely behavior                      |
| --------- | ------------------------------------ |
| `99`      | Very few, very large semantic chunks |
| `95`      | Conservative/default                 |
| `90`      | More boundaries                      |
| `80`      | Many boundaries                      |
| `50`      | Very aggressive splitting            |

These are not guaranteed chunk sizes. The result depends entirely on the document's semantic structure.

For your use case, I would test:

```python
95
90
85
```

and compare the output.

---

# 6. `sentence_splitter`

```python
sentence_splitter: Optional[Callable[[str], List[str]]]
```

Before semantic comparison can happen, the document needs to be broken into sentences.

By default, LlamaIndex provides its own sentence splitting behavior.

You can also provide your own function.

The required conceptual interface is:

```python
def sentence_splitter(
    text: str
) -> list[str]:
    ...
```

Input:

```text
"Hello world. This is another sentence."
```

Output:

```python
[
    "Hello world.",
    "This is another sentence."
]
```

You might provide a custom splitter if your documents contain:

* scientific abbreviations
* equations
* unusual punctuation
* programming code
* badly extracted PDF text
* specialized terminology

For example, a naive sentence splitter might incorrectly interpret:

```text
Fig. 3 shows...
```

as:

```text
Sentence 1: Fig.
Sentence 2: 3 shows...
```

For ordinary prose, the default splitter is usually the right starting point.

---

# 7. `include_metadata`

```python
include_metadata: bool = True
```

This controls whether metadata from the original document is included in the resulting Nodes.

Suppose your input is:

```python
Document(
    text="Neural networks are...",
    metadata={
        "book": "Introduction to AI",
        "chapter": "Machine Learning",
        "page": 42
    }
)
```

If:

```python
include_metadata=True
```

the resulting Nodes can retain metadata:

```python
node.metadata
```

approximately:

```python
{
    "book": "Introduction to AI",
    "chapter": "Machine Learning",
    "page": 42
}
```

This is particularly useful for your project.

Your eventual vector record could preserve:

```json
{
    "text": "Neural networks consist of...",
    "metadata": {
        "book": "Computer Science",
        "chapter": "Artificial Intelligence",
        "section": "Neural Networks",
        "page": 42
    }
}
```

That allows you to later retrieve a chunk and know where it came from.

I would generally keep:

```python
include_metadata=True
```

---

## Important nuance

The schema description says:

> Whether or not to consider metadata when splitting.

This is related to LlamaIndex's metadata-aware node handling. In practice, metadata handling can affect how document information is propagated and represented during parsing.

For ordinary semantic chunking, you should think of this parameter primarily as controlling whether metadata is preserved/used in the node parsing pipeline.

For your textbook use case, keeping metadata is generally preferable.

---

# 8. `include_prev_next_rel`

```python
include_prev_next_rel: bool = True
```

This adds relationships between neighboring Nodes.

Suppose the document produces:

```text
Node 1
Node 2
Node 3
```

With:

```python
include_prev_next_rel=True
```

LlamaIndex can establish:

```text
Node 1
   │
   └── NEXT → Node 2


Node 2
   │
   ├── PREVIOUS → Node 1
   │
   └── NEXT → Node 3


Node 3
   │
   └── PREVIOUS → Node 2
```

This is useful because vector search may retrieve:

```text
Node 2
```

but sometimes you need the surrounding context.

You could conceptually expand the result:

```text
Retrieved:
    Node 2

Also retrieve:
    Node 1
    Node 3
```

For document retrieval, I would generally leave this:

```python
include_prev_next_rel=True
```

---

# 9. `callback_manager`

```python
callback_manager: CallbackManager
```

This is mostly for observability and instrumentation.

LlamaIndex uses callbacks to track events in the pipeline.

For example, you might want to monitor:

```text
Document parsing started
Sentence splitting completed
Embedding started
Embedding completed
Nodes created
```

Or collect:

* timing information
* tracing
* debugging information
* token usage
* pipeline events

For a basic implementation, you usually do not need to configure this manually.

---

# 10. `class_name`

The model exposes:

```python
class_name()
```

which returns a stable identifier:

```text
SemanticSplitterNodeParser
```

This is primarily used for serialization and component identification.

It is not something you normally configure for everyday usage.

---

# 11. `original_text_metadata_key`

This appears in `from_defaults()`:

```python
original_text_metadata_key: str = "original_text"
```

This is related to preserving the original text information in metadata during processing.

The default key is:

```python
"original_text"
```

Conceptually, metadata might contain:

```python
{
    "original_text": "Original source content..."
}
```

Unless you have a specific reason to change how original source text is stored, you can usually leave the default.

---

# 12. `id_func`

```python
id_func: Optional[
    Callable[[int, Document], str]
]
```

This lets you control how generated Nodes receive IDs.

For example:

```python
def my_id_func(
    index: int,
    document: Document
) -> str:

    return f"{document.metadata['book_id']}_node_{index}"
```

Then your generated Nodes might have IDs like:

```text
book_001_node_0
book_001_node_1
book_001_node_2
```

Without a custom function, LlamaIndex generates IDs automatically.

This becomes useful when you want deterministic IDs for:

* Qdrant
* databases
* incremental updates
* avoiding duplicate chunks
* reproducible indexing

For your project, deterministic IDs may eventually be useful.

---

# 13. `from_defaults()`

The easiest way to create the parser is:

```python
SemanticSplitterNodeParser.from_defaults(...)
```

For example:

```python
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser,
)

from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding,
)


embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)


splitter = SemanticSplitterNodeParser.from_defaults(
    embed_model=embed_model,
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    include_metadata=True,
    include_prev_next_rel=True,
)
```

This creates a configured semantic node parser.

---

# 14. `build_semantic_nodes_from_documents()`

The method shown in the documentation is:

```python
build_semantic_nodes_from_documents(
    documents,
    show_progress=False
)
```

It takes:

```python
Sequence[Document]
```

For example:

```python
documents = [
    Document(text="Document 1..."),
    Document(text="Document 2...")
]
```

Then:

```python
nodes = splitter.build_semantic_nodes_from_documents(
    documents,
    show_progress=True
)
```

The output is:

```python
List[BaseNode]
```

Conceptually:

```python
[
    TextNode(...),
    TextNode(...),
    TextNode(...)
]
```

The nodes contain text plus associated metadata and relationships.

In typical LlamaIndex usage, you may also encounter:

```python
get_nodes_from_documents()
```

which is the general node-parser interface.

For practical code, I would usually start with:

```python
nodes = splitter.get_nodes_from_documents(
    documents
)
```

because that is the standard interface shared by node parsers.

---

# A complete minimal example

First install the core package and HuggingFace embedding integration:

```bash
pip install llama-index-core llama-index-embeddings-huggingface
```

Then:

```python
from llama_index.core import Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


# 1. Create an embedding model.
# The semantic splitter uses this model to detect semantic changes.
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)


# 2. Create the semantic splitter.
splitter = SemanticSplitterNodeParser.from_defaults(
    embed_model=embed_model,

    # Number of surrounding sentences considered
    # when evaluating semantic similarity.
    buffer_size=1,

    # Higher = fewer/larger chunks.
    # Lower = more/smaller chunks.
    breakpoint_percentile_threshold=95,

    # Preserve document metadata.
    include_metadata=True,

    # Create PREVIOUS/NEXT relationships between nodes.
    include_prev_next_rel=True,
)


# 3. Create a LlamaIndex Document.
document = Document(
    text="""
    Neural networks are computational models inspired by
    biological nervous systems. They consist of interconnected
    artificial neurons organized into layers.

    Each connection has an associated weight. During training,
    these weights are adjusted to minimize prediction error.
    Backpropagation is commonly used to calculate gradients.

    Decision trees are another machine learning model. They
    recursively divide data according to feature values.
    Information gain can be used to select splits.
    """,

    metadata={
        "book": "Machine Learning",
        "chapter": "Machine Learning Models"
    }
)


# 4. Convert the document into semantic nodes.
nodes = splitter.get_nodes_from_documents(
    [document]
)


# 5. Inspect the results.
for index, node in enumerate(nodes, start=1):

    print(f"\n{'=' * 60}")
    print(f"NODE {index}")
    print(f"{'=' * 60}")

    print(node.get_content())

    print("\nMetadata:")
    print(node.metadata)

    print("\nRelationships:")
    print(node.relationships)
```

The output will be semantically determined rather than fixed at, for example, 500 tokens.

---

# What I would use for your books

For your use case, I would initially configure it like this:

```python
splitter = SemanticSplitterNodeParser.from_defaults(
    embed_model=embed_model,
    buffer_size=1,
    breakpoint_percentile_threshold=90,
    include_metadata=True,
    include_prev_next_rel=True,
)
```

Why `90` rather than the default `95`?

A textbook often has subtopics such as:

```text
Machine Learning
    │
    ├── Supervised Learning
    │
    ├── Unsupervised Learning
    │
    ├── Neural Networks
    │
    └── Decision Trees
```

A threshold of `95` may only identify the largest semantic transitions. Starting around `90` may produce finer topic-level segmentation.

But this must be evaluated on your actual documents. The correct value is empirical.

A useful experiment would be:

```text
Same document

Threshold 95
    ↓
Inspect chunks

Threshold 90
    ↓
Inspect chunks

Threshold 85
    ↓
Inspect chunks
```

Then compare:

* number of Nodes
* average token length
* whether concept boundaries are preserved
* whether unrelated concepts appear in the same Node
* whether one concept gets fragmented excessively

One important limitation remains: `SemanticSplitterNodeParser` **does not guarantee one chunk per concept**. It detects **semantic discontinuities**, not your ontology concepts. For your Semantica pipeline, the next useful step would be to run this semantic splitter on the document you already extract with Docling, preserve the chapter/section/page metadata on every `Document` or structural unit, and then inspect whether the resulting Nodes align sufficiently with your extracted curriculum concepts.

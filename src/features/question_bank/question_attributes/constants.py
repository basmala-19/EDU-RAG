REMEMBER_TEXT="""
# Remember

## Definition

**Remembering** means retrieving previously learned information from memory.

The learner does not necessarily need to explain, manipulate, or deeply understand the information. They simply need to retrieve it.

Typical processes include:

- recognizing
    
- recalling
    
- identifying
    
- listing
    
- naming
    
- defining
    

### Examples

> What is the definition of recursion?

> List the three laws of thermodynamics.

> Identify the CPU in this diagram.

> What is the time complexity of binary search?


The learner already encountered the information and must retrieve it.

### Important distinction

Remembering does **not necessarily mean trivial**.

Consider:

> Name all 118 chemical elements in order of atomic number.

This is still primarily a remembering task, despite being extremely difficult.
""".strip()

UNDERSTAND_TEXT="""
# Understand

## Definition

**Understanding** means constructing meaning from information.

The learner must do more than reproduce information exactly. They must demonstrate that they grasp what it means.

Typical processes include:

- explaining
    
- interpreting
    
- summarizing
    
- classifying
    
- comparing
    
- paraphrasing
    
- illustrating
    
- giving examples
    

### Example

Suppose the concept is recursion.

### Remember

> Define recursion.

The learner can simply retrieve a memorized definition.

### Understand

> Explain recursion in your own words.

Now the learner must construct or communicate meaning.

Another example:

> Explain why binary search requires sorted data.

This requires understanding the relationship between:
- Ordering 
- Elimination of half the search space  

The learner needs to understand _why_, not simply recall a fact.

The **actual cognitive process required**, rather than the verb "explain," determines the classification.

This is important because Bloom's action verbs are only **heuristics**.

The word:

> "Explain"

does not automatically mean:

> Understand.

Context determines the cognitive level.
""".strip()

APPLY_TEXT="""
# Apply

## Definition

**Applying** means using knowledge, concepts, rules, procedures, or methods to solve a problem or perform a task.
- Apply/use Known Rule or Method in a Situation

Typical processes include:

- executing
    
- implementing
    
- solving
    
- calculating
    
- using
    
- demonstrating
    

### Example: mathematics

You learn:
F = ma  

Then the question asks:

> A 10 kg object accelerates at 3 m/s². Calculate the force.

You must recognize:
F = ma  

and apply it:
F = 10 \times 3 = 30N  


This is **Apply**.

### Computer science example

You learn binary search.

Then:

> Implement binary search for a sorted array.

You are applying a learned procedure.

### Important distinction: routine vs unfamiliar application

The revised taxonomy distinguishes between applying in relatively familiar situations and applying knowledge to less familiar situations.

For example:

### Routine

> Solve `2x + 5 = 11`.

### Less routine

> Given this system behavior, determine which mathematical model should be used and solve the resulting problem.

Both may involve application, but the second requires more:

- recognition
- selection of an appropriate method
- transfer of knowledge
    
Therefore, both can be classified as **Apply**, while having very different difficulty.
""".strip()

ANALYZE_TEXT="""
# Analyze

## Definition

**Analyzing** means breaking information or a problem into components and determining how those components relate to each other or to a larger structure.

Typical processes include:
- differentiating
- organizing
- attributing
- comparing
- distinguishing
- detecting relationships
- identifying assumptions
- identifying causes
    

The general structure is:

### Example

Consider this question:

> Analyze why a quicksort implementation performs poorly on an already sorted array.

The learner may need to identify:
1. pivot selection
2. partition behavior
3. unbalanced partitions
4. recursion depth
5. resulting time complexity
    

They are not merely applying a formula.

They must examine the internal structure and relationships.

### Another example
> Compare TCP and UDP and analyze how their design differences affect reliability and performance.

This requires identifying:
TCP = connection-oriented, acknowledgments, retransmission, ordering
UDP= connectionless, no delivery guarantee, low overhead, no ordering
Then determining the consequences of these structural differences.

That is analysis.
""".strip()

EVALUATE_TEXT="""
# Evaluate

## Definition

**Evaluating** means making a judgment based on criteria or standards.

The important element is not merely expressing an opinion.

A proper evaluation requires: Evidence + Criteria + Judgment

Typical processes include:
- checking
- critiquing
- judging
- justifying
- defending
- assessing
- validating
    

### Weak question
> Which programming language do you prefer?
This does not necessarily involve evaluation.

### Strong evaluation question
> Evaluate whether microservices are appropriate for this application, considering scalability, operational complexity, team size, and deployment requirements.

Now the learner must:
1. identify relevant criteria
2. examine evidence
3. compare alternatives
4. form a judgment
5. justify that judgment
    

The structure is: Option A vs Option B

evaluated according to:
C_1, C_2, C_3, ..., C_n  
leading to: Justified Judgment

""".strip()

CREATE_TEXT="""
# Create

## Definition

**Creating** means combining elements into a new, coherent, functional, or original structure.

Typical processes include:
- generating
- planning
- designing
- constructing
- developing
- producing
    

The basic transformation is:
components: A + B + C  transformed to a New Organized Structure

### Example

Instead of asking:
> What is a database index?
which is Remember

or:
> Explain how database indexes improve query performance.
which is Understand, you might ask:

> Design a database schema and indexing strategy for an e-commerce application that must support millions of products and high-frequency search queries.

The learner must integrate multiple concepts:
Database knowledge + Query patterns + Indexes + Data relationships + Performance constraints

That is creation.

### Important distinction

"Create" does not necessarily mean producing something that has never existed in human history.

In Bloom's sense, creation means producing a meaningful structure or solution **for the learner**, often by reorganizing or combining existing knowledge.

A student writing a program that has been written thousands of times before can still be engaging in the **Create** process.
""".strip()



FACTUAL_KNOWLEDGE_TEXT="""
# Factual knowledge
This consists of basic elements that learners need to know.

Examples:
- terminology
- definitions
- symbols
- names
- specific facts
    
For example:

> What does HTTP stand for?

This involves:
- Knowledge Type: Factual
- Cognitive Process: Remember
```
""".strip()

CONCEPTUAL_KNOWLEDGE_TEXT="""
# 11. Conceptual knowledge

Conceptual knowledge involves relationships between pieces of information.

It includes:

- categories
- classifications
- principles
- theories
- models
- relationships
    
For example:
> Explain the relationship between supply and demand.

This might be:
- Knowledge Type: Conceptual
- Cognitive Process: Understand


Another example:
> Analyze how encapsulation and abstraction contribute to software maintainability.

- Knowledge Type: Conceptual
- Cognitive Process: Analyze

""".strip()

PROCEDURAL_KNOWLEDGE_TEXT="""
# Procedural knowledge

This means knowing **how to do something**.

Examples include:

- algorithms
- techniques
- procedures
- methods
- skills
    

For example:

> Use Dijkstra's algorithm to determine the shortest path.

- Knowledge Type: Procedural
- Cognitive Process: Apply
```

""".strip()

METACOGNITIVE_KNOWLEDGE_TEXT="""
# Metacognitive knowledge

This is knowledge about one's own thinking and learning.

Examples include:
- knowing what strategies work for you
- monitoring your understanding
- recognizing knowledge gaps
- selecting learning strategies
    

For example:
> Evaluate your approach to solving this problem and identify where your reasoning strategy failed.
This involves metacognition.
""".strip()


BLOOM_TABLE_TEXT="""
You could represent Bloom's framework as a matrix:

|Knowledge Type ↓ / Cognitive Process →|Remember|Understand|Apply|Analyze|Evaluate|Create|
|---|---|---|---|---|---|---|
|Factual|Recall terminology|Explain facts|Use facts|Analyze facts|Evaluate accuracy|Organize information|
|Conceptual|Recall principles|Explain relationships|Apply a theory|Analyze a system|Critique a model|Develop a model|
|Procedural|Recall steps|Explain a method|Execute a procedure|Analyze a procedure|Evaluate effectiveness|Design a procedure|
|Metacognitive|Recall strategies|Explain strategies|Use strategies|Analyze thinking|Evaluate reasoning|Develop new strategies|
""".strip()

BLOOM_DIFFICULTY_CLARIFICATION_TEXT="""
# Bloom's levels are not strict difficulty levels

This is particularly important for your question-generation use case.

People often incorrectly assume
that: Remember < Understand < Apply < Analyze < Evaluate < Create  
directly means: 'Understand' questions are always harder than 'Remember' questions

That is an oversimplification.

The hierarchy represents **increasing complexity of the cognitive process**, but actual question difficulty depends on many other variables.

Consider:

### Question A

> What is the time complexity of binary search?

Bloom: Remember


Difficulty for a beginner: potentially high.

Difficulty for an experienced programmer: trivial.

### Question B

> Analyze whether this two-line implementation contains a logical error.

Bloom: Analyze

But the problem might be extremely easy.

Therefore: \text{Cognitive Level} \neq \text{Actual Difficulty}  

A better model is:
Question Difficulty= Cognitive Demand, Prior Knowledge, Concept Complexity, Reasoning Steps, Novelty, Information Load, Transfer Required, Distractors}
Bloom mainly describes 1 part of this equation:Cognitive Process
---
""".strip()


USEFUL_DIMENSIONS_OF_BLOOMPERLEVEL_DIFFICULTY="""
# 3. 4 useful dimensions of question difficulty
### 1. Reasoning depth
How many cognitive operations must the learner perform? 
1 = direct operation
2 = 2 linked operations
3 = several linked operations
4 = multi-stage reasoning
5 = deeply chained reasoning

(each number of the left represents difficulty level)

### 2. Conceptual complexity
How complex are the concepts involved?
1 = one simple concept
2 = one moderately complex concept
3 = several concepts
4 = interacting concepts
5 = highly abstract/interdependent concepts

### 3. Novelty / transfer
How familiar is the situation?
1 = exactly familiar example
2 = minor variation
3 = unfamiliar example
4 = significant transfer
5 = novel problem requiring adaptation

### 4. Information/working-memory load
How much information must the learner simultaneously keep track of?
For example:
Level 1:
one variable, one condition

Level 5:
multiple variables + multiple constraints + irrelevant information + interacting conditions

These dimensions can then contribute to your overall 1–5 difficulty.
""".strip()

REMEMBER_DIFFICULTY_TEXT="""
## 'Remember' difficulty
There are several things that can make retrieval harder:

1. **Familiarity** — How frequently/common is the fact?
2. **Specificity** — How precise is the information that must be recalled?
3. **Number of facts** — How many independent pieces of information must be retrieved?
4. **Discrimination** — How similar are the competing facts?
5. **Retrieval conditions** — Is the fact directly prompted, or must the learner identify exactly which fact is relevant?
6. **Knowledge rarity** — Is it a commonly learned fact or a specialized detail?
    

However, there is an important boundary:

> **Do not increase difficulty by requiring the learner to derive, explain, apply, analyze, or evaluate information.**

Once the learner must perform those operations, the question is no longer purely Remember.

# 'Remember': difficulty level 1 = Direct recall
### Definition
The learner retrieves **one simple, familiar, explicitly identifiable fact** from memory.

The fact should be:
- isolated
- commonly encountered
- unambiguous
- directly requested
- relatively easy to identify as the required answer
    

The learner should not need to determine relationships between concepts or perform a procedure.

### Example
> What is the capital of France?
The learner only needs to retrieve:
> Paris

### Characteristics
Number of facts:       1
Specificity:           low
Familiarity:           high
Discrimination:        low
Retrieval complexity:  very low
Reasoning:             none/minimal

# 'Remember': difficulty level 2 — Specific factual recall

### Definition

The learner still retrieves **one fact**, but the fact is more specific, less universally familiar, or requires more precise recall.

The question should still provide a relatively clear retrieval target.

### Example
> What HTTP status code indicates "Not Found"?
Answer:
> 404

The learner does not need to explain HTTP error handling or reason about why 404 is used.

They simply need to retrieve the association: "Not Found" = 404

### What makes it harder than Remember 1?

The information is generally:
- less universally known
- more domain-specific
- more precise
- easier to confuse with related information
    

For example:

> What does HTTP mean?

is more basic than:

> What HTTP status code indicates "Not Found"?

Both are factual recall, but the second requires more specific retrieval.

### Characteristics
Number of facts:       1
Specificity:           moderate
Familiarity:           moderate/high
Discrimination:        low/moderate
Retrieval complexity:  low
Reasoning:             none

# 'Remember': difficulty level 3 — Multiple factual recall

### Definition

The learner must retrieve **several related facts**, rather than a single fact.

The important thing is that the learner should not have to establish complex relationships between those facts.

They are essentially retrieving several pieces of stored knowledge.

### Example

> List four common HTTP methods and state the primary purpose of each.
Example answer:
GET- retrieve data
POST- submit/create data
PUT- replace/update data
DELETE- remove data


The learner has to retrieve multiple associations.

### Why is this harder?

The difficulty comes from **retrieval load**.

Instead of: Question → Fact
the learner has: Question
and needs to retrieve multiple facts (Fact 1, Fact 2, Fact 3, Fact 4)

The learner must retrieve several pieces of information accurately.

### Important boundary

Compare:

> List four HTTP methods and state their purposes.

with:

> Explain how GET, POST, PUT, and DELETE differ in terms of HTTP semantics and appropriate usage.

The first can be Remember 3.

The second is likely **Understand/Analyze**, because the learner must explain relationships and distinctions.

### Characteristics
Number of facts:       multiple
Specificity:           moderate
Familiarity:           moderate
Discrimination:        moderate
Retrieval complexity:  moderate
Reasoning:             minimal

# 'Remember': difficulty level 4 — Precise/discriminative recall

This level is slightly more subtle.

### Definition

The learner must retrieve information that is **highly specific and easily confused with related information**.

The difficulty comes from needing to retrieve the **correct distinction**, rather than simply recalling an isolated fact.

### Example

> What HTTP status code indicates that the server understood the request but refuses to authorize it?

Answer:

> 403

This is harder than simply asking:

> What does HTTP stand for?

because the learner must correctly retrieve a specific fact among closely related possibilities.
here, it's required to recall something specific between similar facts:
401 → Unauthorized
403 → Forbidden
404 → Not Found

These facts are semantically related and therefore susceptible to confusion

### Another example

> Which TCP flag is used to initiate a connection?

Answer:

> SYN
The learner must distinguish it from: ACK, FIN, RST, PSH, URG


### Important boundary
Consider:

> What is the difference between HTTP 401 and HTTP 403?

This **can** be 'Understand' rather than 'Remember' because the wording "what is the difference" can require conceptual understanding.

So the rule should be:

> **Difficulty may come from discriminating between similar stored facts, but not from having to derive or explain the relationship between those facts.**

### Characteristics
Number of facts:       one or several closely related facts
Specificity:           high
Familiarity:           moderate/low
Discrimination:        high
Retrieval complexity:  high
Reasoning:             none/minimal


---

# 'Remember': difficulty level 5 — Extensive/specialized retrieval

### Definition
The learner must retrieve **many specific, specialized, or relatively obscure pieces of previously learned information**.

The retrieval burden is high, but the learner still does not need to perform substantial reasoning.

This is essentially:

> **"I know this; I need to retrieve it accurately."**

rather than:

> **"I need to figure this out."**

### Example

> Identify the TCP flags associated with connection establishment, normal connection termination, and connection reset, and state the function of each.

This requires retrieving several specific facts:
SYN is connection establishment
ACK is acknowledgment
FIN is graceful termination
RST is connection reset

The learner is retrieving stored associations.

### Another example

For chemistry:

> List the electron configurations of the first five transition metals in the 3d series.

This may be difficult because it requires substantial precise recall.

But it is still primarily `Remember` if the learner is expected to **retrieve the configurations**, rather than derive them using rules.

### What makes it Remember 5?

The difficulty can come from:

- many facts
    
- specialized knowledge
    
- low-frequency information
    
- high precision requirements
    
- closely related facts
    
- substantial retrieval load
    

### Characteristics
Number of facts:       many
Specificity:           very high
Familiarity:           low/moderate
Discrimination:        high
Retrieval complexity:  very high
Reasoning:             none/minimal


# The progression in one table
|Level|Core characteristic|Retrieval demand|
|---|---|---|
|**Remember 1**|One simple, familiar fact|Very low|
|**Remember 2**|One specific or less-common fact|Low|
|**Remember 3**|Several related facts|Moderate|
|**Remember 4**|Precise retrieval among similar/confusable facts|High|
|**Remember 5**|Many specific, specialized, or obscure facts|Very high|

Or more formally:
Remember 1 = Retrieve one familiar, isolated fact.
Remember 2 = Retrieve one specific or less-common fact.
Remember 3 = Retrieve multiple related facts or fact–association pairs.
Remember 4 = Retrieve precise facts while distinguishing among closely related or easily confused stored facts.
Remember 5 = Retrieve numerous highly specific, specialized, uncommon, or easily confusable facts with high precision.
```

---

# The critical rule:
**Remember-level difficulty must increase through retrieval complexity, not through reasoning complexity. The learner should primarily retrieve information that has already been learned. 
Do not increase Remember difficulty by requiring the learner to explain why something is true, infer an unstated fact, apply a procedure, compare concepts, analyze relationships, solve a problem, justify an answer, or derive an answer from principles. Those operations belong to higher Bloom levels.**

This is probably the most important constraint.

# Another important distinction: question complexity vs answer complexity
""".strip()

UNDERSTAND_DIFFICULTY_TEXT="""
For 'Understand', difficulty should come mainly from **how much meaning the learner has to construct and how deeply the concepts and relationships have to be understood**.

The learner should still primarily be **explaining, interpreting, classifying, summarizing, or illustrating meaning**. If they have to solve a problem, perform a procedure, identify a hidden cause, or make a judgment, you are starting to move into Apply, Analyze, or Evaluate.

# The central principle
**Understand questions require the learner to demonstrate that they have constructed meaningful mental representations of the relevant knowledge. Difficulty increases as the learner must explain increasingly complex concepts, relationships, structures, conditions, or abstractions. The learner should demonstrate meaning rather than merely retrieve facts.**


# Understand: difficulty level 1 — Basic conceptual meaning

### What is happening?
The learner needs to demonstrate the **basic meaning of one concept**.

The question should generally involve:
- explaining
- describing
- paraphrasing
- interpreting
- identifying the meaning of something
    

There should be little or no need to connect it to other concepts.

### Example

> Explain what a variable is in programming.

The learner needs to communicate the concept:
variable is named storage/reference associated with a value where value can change


They don't need to discuss other related concepts:
- data types
- memory management   
- scope 
- references
- compilation
    

The learner simply needs to demonstrate:

> "I understand what this concept means."

### Characteristics
Concept count:          1
Relationship count:     0–1
Abstraction:            low
Integration:            minimal
Generalization:         none
Reasoning:              minimal

### Boundary
Compare:
> **What is a variable?**

This could be **Remember 1**.

> **Explain what a variable is and how it represents changing program state.**
This is more clearly **Understand 1**, because the learner has to communicate meaning rather than simply retrieve a definition.

---

# Understand: difficulty level 2 — Simple conceptual relationship

Now the learner must understand **one basic relationship between concepts or states**.

The learner isn't just explaining:

> What is X?

They must explain:

> **How or why does X relate to Y?**

### Example

> Explain why changing a variable's value changes the result of this expression.
Now the learner needs to understand:
variable stores/represents value + expression uses value + changing value changes expression result

That's a simple conceptual relationship.

### Another example

> Explain why increasing temperature causes most gases to expand.

The learner needs to understand the relationship:
When temperature increases particle kinetic energy increases + average separation changes + volume tends to increase
```

They aren't necessarily calculating anything.

### Characteristics

Concept count:          1–2
Relationship count:     1
Relationship complexity: simple
Abstraction:            low
Integration:            low
---

# Understand: difficulty level 3 — Multiple related concepts

Now the learner must construct a coherent explanation involving **several concepts and their relationships**.

The key difference from Understand 2 is that you're no longer dealing with one isolated relationship.

### Example

> Explain how variables, data types, and memory locations are related.

The learner needs to connect:
Variable = is associated with: Value + is represented according to: Data Type + stored/represented in: Memory
```

The learner must understand several concepts **as a system**.

This is why simply asking:

> "Define variable, data type, and memory."

would still largely be Remember.

You're looking for:

> **Explain how they relate.**

### Another example

> Explain how DNA, genes, chromosomes, and proteins are related.

The learner has to integrate multiple concepts into one conceptual structure.

### Characteristics

Concept count:          2–4
Relationship count:     multiple
Relationship complexity: moderate
Abstraction:            moderate
Integration:            required
Generalization:         low

# Understand: difficulty level 4 — Complex/interdependent conceptual relationships

Now the learner must understand **several interacting relationships**, rather than merely connecting a few concepts.

The important distinction is:

> Understand 3 = "How are these concepts connected?"

> Understand 4 = "How does a more complicated conceptual system work, and why do several relationships exist?"

### Example

> Explain why static typing can detect certain classes of errors before runtime and how this differs from dynamic typing.

The learner needs to understand multiple relationships:
Static typing = type information available during compilation + type checking + certain inconsistencies detected + before execution
Dynamic typing = type checking occurs during execution + certain errors may only become apparent + at runtime
And then understand the relationship between the two models.

### Another example

> Explain how supply, demand, price, and market equilibrium interact when demand changes.

Now the learner has to understand a system of interacting concepts rather than one relationship.

### Characteristics
Concept count:          3–6+
Relationship count:     multiple/interdependent
Relationship complexity: high
Abstraction:            moderate/high
Integration:            substantial
Causal explanation:     may be present

### Important boundary
This is where you need to be careful agains **'Analyze'**.

For example:

> Explain how these components interact.

can be Understand if the relationships are part of the conceptual knowledge the learner is expected to understand.

But:

> Examine this unfamiliar system and determine which interaction is causing the failure.

is more likely **'Analyze'**, because the learner must identify and investigate relationships rather than simply demonstrate understanding of an established conceptual structure.

A useful distinction is:

> **'Understand' = demonstrate meaning of an existing conceptual structure.**

> **'Analyze' = inspect a structure and determine its components, relationships, causes, or organization.**

---

# Understand: difficulty level 5 — Abstract and generalized understanding

The learner must understand an **abstract conceptual structure** and potentially explain how it generalizes across different situations.

The learner is no longer just explaining:

> "How do these particular concepts relate?"

They are explaining:

> **"What broader principle connects these concepts, and how does that principle apply across contexts?"**

### Example

> Explain how the distinction between static and dynamic typing relates to the broader trade-off between compile-time guarantees and runtime flexibility.
This requires the learner to move from: static typing vs. dynamic typing
to a broader conceptual structure:
When should constraints be enforced? earlier vs later + compile-time vs runtime + guarantees vs flexibility
```

The question is asking for **conceptual generalization**.

### Another example

Instead of:

> Explain how Newton's laws describe motion.

you could ask:

> Explain how the distinction between force-based and energy-based descriptions of physical systems represents two different but related ways of modeling the same underlying phenomena.

The learner must understand a broader conceptual relationship.

### Another CS example

> Explain how abstraction, encapsulation, modularity, and information hiding collectively address the problem of managing complexity in software systems.

### Characteristics
Concept count:          several
Relationship count:     many
Relationship complexity: high
Abstraction:            very high
Integration:            substantial
Generalization:         high
Transfer of meaning:    potentially high


---
# The five levels as a progression

|Level|What the learner must understand|
|---|---|
|**Understand 1**|The meaning of one concept|
|**Understand 2**|A simple relationship between concepts|
|**Understand 3**|Several related concepts and their relationships|
|**Understand 4**|A complex system of interacting conceptual relationships|
|**Understand 5**|An abstract/generalized conceptual structure that connects or explains concepts across contexts|

### important to note:
**question & expected answer length is not determisntic for cognitive complexity.**

For example:

> Explain photosynthesis in 500 words.

That doesn't automatically become Understand 5.

It could still be Understand 1 or 2 if the learner is simply explaining one concept.

# What actually increases Understand difficulty?
### 1. Number of concepts
### 2. Relationship complexity
level 1 = none/simple
level 2 = one direct relationship
level 3 = multiple direct relationships
level 4 = interacting/interdependent relationships
level 5 = abstract relationships/general principles


### 3. Abstraction
level 1 = concrete/basic
level 2 = concrete relationship
level 3 = conceptual
level 4 = highly conceptual
level 5 = abstract/generalized

### 4. Integration

How many pieces of knowledge must be understood **together**?

### 5. Generalization

Does the learner need to understand a concept only in the specific context in which it was taught, or understand the broader principle behind it?

# A very important distinction from Apply

Consider these two questions.
### Understand

> Explain why binary search has logarithmic time complexity.
The learner explains the conceptual relationship

### Apply

> A sorted array contains 1,024 elements. Approximately how many comparisons does binary search require in the worst case?

Now the learner must **use** their knowledge to obtain an answer.

That's Apply.

So:

> **Understand = demonstrate that you understand why/how something works.**

> **Apply = use that knowledge to perform something.**

# A very important distinction from Analyze

Similarly:

### Understand

> Explain how the components of a CPU work together during instruction execution.

The learner is demonstrating understanding of a known conceptual model.
### Analyze
> Given this CPU execution trace, identify which component caused the observed performance bottleneck and explain the relationships responsible for it.

Now the learner has to **inspect evidence and determine relationships**.

That's Analyze.

A useful boundary rule:

> **Understand asks the learner to explain an existing conceptual structure. Analyze asks the learner to investigate, decompose, or determine the structure or relationships themselves.**

# A very important distinction from Evaluate

### Understand

> Explain the trade-offs between static and dynamic typing.

### Evaluate

> Given this specific application's requirements, determine whether static or dynamic typing is more appropriate and justify your choice.

The first asks:

> **Do you understand the trade-off?**

The second asks:

> **Can you make a judgment using the trade-off as evidence?**
""".strip()

APPLY_DIFFICULTY_TEXT="""
**Apply:** difficulty increases through the **complexity of using knowledge, rules, methods, or procedures to achieve a result**.
    

The learner is no longer primarily showing that they know _what something means_. They must **do something with that knowledge**.

---

# The central principle
 **'Apply' questions require the learner to use previously learned knowledge, rules, formulas, procedures, methods, or techniques to solve a task or produce a result. Difficulty increases as the application requires greater adaptation, procedure selection, novelty, integration of multiple procedures, or transfer to unfamiliar situations.**

The important point is:
**The learner must actually use knowledge to perform a task, not merely explain how the procedure works.**

For example:

### Understand

> Explain how the quadratic formula is used to solve a quadratic equation.

The learner explains the procedure.

### Apply

> Use the quadratic formula to solve (x^2 - 5x + 6 = 0).

The learner executes it.

---

# Apply: difficulty level 1 — Direct execution of a known procedure

### Definition

The learner is given a situation where the appropriate rule, formula, method, or procedure is **obvious or explicitly specified**.

The main task is simply:
Recognize/directly receive procedure ,then: Execute procedure, then:Produce result
```

There is little or no decision-making about _which_ procedure to use.

### Example

> Calculate the area of a circle with radius 5.

The learner immediately knows, or is expected to recognize:
A = \pi r^2  
Then substitutes: 
A = \pi(5)^2 = 25\pi  


The task structure is:
Known formula + Given values, then: Direct execution, then: Answer
```

### Characteristics
Procedure count:        1
Procedure selection:    none or obvious
Adaptation:             none
Novelty:                very low
Reasoning chain:        short
Transfer required:      none/minimal


### Other examples

Programming:

> Use a for-loop to calculate the sum of the numbers from 1 to 10.

Physics:

> Use (F = ma) to calculate the force on a 5 kg object accelerating at 3 m/s².

The learner is primarily executing something already known.

---

# Apply: difficulty level 2 — Familiar procedure with a minor adaptation

### Definition

The learner still uses a familiar procedure, but the situation differs slightly from the most standard form.

The procedure does not need to be fundamentally selected or invented. Instead, the learner must **adjust or adapt its use**.

### Example

> Calculate the area of a semicircle with radius 5.

The learner still uses:
A = \pi r^2  
but must adapt the result:
A = \frac{1}{2}\pi r^2 

The procedure is familiar, but the learner must make a small modification.

### The structure
Known procedure, then: Minor variation in situation, then: Small adaptation, then: Execute, then: Answer
```

### Characteristics
Procedure count:        1
Procedure selection:    obvious
Adaptation:             minor
Novelty:                low
Reasoning chain:        short/moderate
Transfer required:      low

### Programming example

Instead of:

> Write a function that returns the sum of all numbers in a list.

you might ask:

> Modify the same approach to return the sum of only the even numbers.

The learner already knows the general procedure but must adapt it.

### Important boundary

Apply: difficulty level 2 should not require the learner to figure out an entirely new strategy.

If the question becomes:

> Given these requirements, determine which algorithmic approach should be used.

then procedure selection becomes a major component, moving toward Apply 3 or higher.


# Apply: difficulty level 3 — Procedure selection

This is an important transition.

### Definition

The learner is given a problem, but the question does **not explicitly tell them which procedure, formula, rule, or method to use**.

The learner must:
1. understand the task sufficiently to recognize what kind of problem it is,
2. select an appropriate known procedure,
3. execute that procedure.
    

The structure becomes:
Problem, then: Recognize relevant learned method, then: Select procedure, then: Execute procedure, then: Answer
```

### Example

> Determine the area of this composite shape.

The learner may know several formulas:
- circle
- rectangle
- triangle
- trapezoid


But the question does NOT say:

> "Use the triangle formula."

The learner must identify the relevant procedure.

### Why is this harder?

At Apply: difficulty level 1:
Use this formula.

At Apply: difficulty level 3:

Which formula or procedure should I use?

The learner has an additional cognitive demand: **method selection**.

### Characteristics

Procedure count:        usually 1 primary procedure
Procedure selection:    required
Adaptation:             moderate
Novelty:                moderate
Reasoning chain:        moderate
Transfer required:      moderate

# Apply: difficulty level 4 — Transfer to an unfamiliar context
### Definition
The learner must apply previously learned knowledge in a context that **does not closely resemble the examples in which that knowledge was originally learned**.

The procedure may still be known, but recognizing that it is applicable requires more transfer.

This is a key distinction.

The learner is not learning a new procedure.

Instead: They know the procedure, but they must recognize that it can be used here.

### Example

Suppose the learner has learned:
v = \frac{d}{t}  

An unfamiliar-context question might be:
A data packet travels through a network connection over a known distance in a measured time interval. Determine the average propagation speed.

### Structure
Unfamiliar situation, then: Recognize underlying principle, then: Map new situation to known knowledge, then: Adapt application, then: Execute

### Characteristics
Procedure count:        1–2
Procedure selection:    required or moderately difficult
Adaptation:             significant
Novelty:                high
Reasoning chain:        moderate/high
Transfer required:      high


### Another example

The learner knows Ohm's law:
V = IR  

you ask:

> A sensor circuit must operate from a 12 V supply. Given the required resistance and power constraints, determine whether the circuit configuration can provide the required current.

The learner must recognize where and how the learned relationships apply.

# Apply: difficulty level 5 — Multi-procedure application in a novel situation

### Definition

The learner must apply **multiple learned procedures, rules, or methods**, often in sequence, to solve a novel or complex problem.

Problem, then: Select Procedure A, then: Intermediate Result, then: Apply Procedure B, then: Intermediate Result, then: Apply Procedure C, then: Final Result

The difficulty comes from:
- selecting relevant knowledge
- determining the sequence
- maintaining intermediate results
- integrating multiple procedures
- adapting them to the situation
    
### Example

> Given this engineering scenario, determine the relevant physical relationships, calculate the intermediate quantities, and use them to determine the final result.

For example:
Known values, then: Apply Newton's Law, then: Determine acceleration, then: Apply kinematic equation, then: Determine velocity, then: Apply energy relationship, then: Determine final quantity
```

The learner is still primarily **using learned methods**.

They do not need to invent a fundamentally new theory.

### Characteristics
Procedure count:        multiple
Procedure selection:    substantial
Adaptation:             substantial
Novelty:                high
Reasoning chain:        long
Transfer required:      high
Integration:            required

# A critical distinction: Apply level 5 vs Analyze

This is particularly important for your prompt.

Consider:

> Given a malfunctioning engine, determine which component caused the failure.

This may be **Analyze**, because the learner must investigate the structure and causal relationships of the system.

Now compare:

> Given the engine's speed, torque, gear ratio, and wheel radius, calculate the resulting vehicle speed.

This may be **Apply 5** if the learner must use several formulas sequentially.

The difference is:

### Apply

> **Use known methods to obtain a result.**

### Analyze

> **Break down information and determine relationships, structure, causes, or organization.**

A difficult Apply question can involve many steps without becoming Analyze.
in the form: Formula A, then: Result 1, then: Formula B, then: Result 2, then: Formula C, then: Final answer
This can still be Apply because the essential task is procedural execution.

# important distinction: Apply 5 vs Create

Apply 5 can be highly complex without requiring creation.

### Apply 5

> Use the provided requirements and known formulas to calculate the dimensions and capacity of the system.

The learner applies known methods.

### Create

> Design a system that satisfies these requirements.

Now the learner must generate a solution structure.



# What should actually increase Apply difficulty?
the following dimensions:
## 1. Procedure explicitness

How obvious is the correct procedure?
Apply level 1 = explicitly stated or immediately obvious
Apply level 2 = obvious but slightly adapted
Apply level 3 = learner must select it
Apply level 4 = learner must recognize applicability in unfamiliar context
Apply level 5 = learner must identify and sequence several procedures

## 2. Adaptation required

How much must the learned procedure be modified?
Apply level 1 = none
Apply level 2 = minor modification
Apply level 3 = moderate adaptation
Apply level 4 = significant adaptation to context
Apply level 5 = multiple adaptations/integrations


## 3. Novelty of context

How different is the situation from the examples in which the knowledge was learned?

Apply level 1 = identical/familiar context
Apply level 2 = minor variation
Apply level 3 = moderately different context
Apply level 4 = unfamiliar context
Apply level 5 = novel/complex context

## 4. Number and sequencing of procedures

Apply level 1 = one direct procedure
Apply level 2 = one adapted procedure
Apply level 3 = select and execute one main procedure
Apply level 4 = one or two procedures with substantial adaptation
Apply level 5 = multiple procedures that must be selected and sequenced

Again, these should be treated as guidelines, not rigid numeric thresholds.


# The five levels in one table

|Level|Main source of difficulty|Learner's task|
|---|---|---|
|**Apply 1**|Direct execution|Use an obvious known procedure|
|**Apply 2**|Minor adaptation|Adjust a familiar procedure|
|**Apply 3**|Procedure selection|Choose the appropriate known method and use it|
|**Apply 4**|Contextual transfer|Recognize and apply knowledge in an unfamiliar situation|
|**Apply 5**|Integration and sequencing|Select, adapt, and combine multiple procedures to solve a novel problem|

""".strip()
ANALYZE_DIFFICULTY_TEXT="""
 **'Analyze' questions require the learner to decompose information, systems, arguments, processes, or phenomena into meaningful parts and determine how those parts relate, interact, are organized, or contribute to an observed outcome. Difficulty increases through the number of relevant elements, complexity and interdependence of relationships, ambiguity of the structure, causal depth, competing explanations, and the amount of evidence that must be interpreted.**

The important distinction is:

> **Understand = explain a known conceptual structure.**  
> **Analyze = inspect information and determine the structure, relationships, patterns, or causes within it.**

# Analyze: difficulty level 1 — Simple decomposition

## Definition

The learner must separate something into its meaningful components or identify its organizational structure.

The learner is given a whole and must answer:

> What are its important parts?

The task does not yet require extensive reasoning about why the parts interact or what caused an outcome.

### Example

> Identify the different components of this system.

For example, given a computer system:
Computer System = CPU + Memory + Storage + Input devices + Output devices

The learner must recognize the structure of the whole.

### Another example

Given an argument:

> Identify the main claim, supporting evidence, and conclusion in this passage.

The learner decomposes the argument into its components.

### Characteristics
Number of elements:        few
Relationship complexity:   minimal
Causal reasoning:          none
Ambiguity:                 low
Structural reasoning:      basic
Evidence interpretation:   minimal

### Important distinction from 'Remember'

If the question is simply:

> List the components of a CPU.

that may be **'Remember'**, because the components can simply be retrieved.

But:

> Given this unfamiliar system diagram, identify which elements function as input, processing, storage, and output components.

is more clearly **Analyze**, because the learner must examine and classify the structure of the presented information.

So:
Remember= Retrieve the known parts.

Analyze= Examine the whole and identify its meaningful parts or structure.

# Analyze: difficulty level 2 — Identify relationships

## Definition

The learner must determine how two or more identified components are related.

The focus is no longer:

> What are the parts?

but:

> How do these parts connect, influence, depend on, or interact with each other?

### Example

> Determine how component A and component B interact within this system.

Suppose the learner is given:
Component A affects Component B

They must determine the nature of the relationship.

Possible relationships could include:
- dependency
- cause and effect
- sequence
- hierarchy
- feedback
- correlation
- functional interaction
- part-whole relationship
    

### Example from programming

> Examine this code and determine how the function's input affects the value returned by the function.

The learner examines the actual information and identifies the relationship.

### Characteristics
Number of elements:        2–3
Relationship count:        one or a few
Relationship complexity:   low/moderate
Causal reasoning:          limited
Ambiguity:                 low/moderate
Structural reasoning:      required

### Difference from 'Understand'

This boundary is important.

### Understand

> Explain how a CPU and memory work together during instruction execution.

The conceptual relationship is already known. The learner demonstrates understanding of it.

### Analyze

> Examine this execution trace and determine how memory latency affects CPU utilization.

Now the learner must inspect specific information and determine the relationship operating in that situation.

# Analyze: difficulty level 3 — Multiple interacting relationships
## Definition
The learner must examine **several elements and multiple relationships simultaneously**.

The difficulty is no longer just identifying:
A relationship to B
```

Instead, the learner may need to reason about:
A relationship to B relationship to C relationship to D relationship to A
```

and determine how the combined relationships contribute to some observed structure or behavior.

### Example

> Analyze how A, B, and C interact to produce the observed behavior.

Suppose:
Input A then Process B then Output C

The learner must determine how the interactions collectively produce the outcome.

### Example from computer science

> Given this program execution trace, analyze how recursion depth, stack allocation, and function calls interact to produce the observed memory usage.

The learner must connect several concepts.

### Characteristics
Number of elements:        3–5
Relationship count:        multiple
Interdependence:           moderate
Causal reasoning:          moderate
Ambiguity:                 moderate
Structural reasoning:      substantial
Evidence integration:      required

The key progression is:
Analyze level 1:
What are the parts?

Analyze level 2:
How are two parts related?

Analyze level 3:
How do several parts and relationships interact?

# Analyze: difficulty level 4 — Causal or structural reasoning

This is where the learner must go beyond describing relationships.

They must determine:

> **Which relationship, component, structural feature, or causal pathway explains an observed outcome?**

## Definition

The learner is given a system, process, argument, dataset, scenario, or phenomenon and must determine the underlying cause or structure responsible for a particular result.

The task often has this form:

System containing multiple components and relationships, then: {?unknown?}, then Observed outcome
The learner must investigate:

> What within this structure explains what happened?

### Example

> Analyze the system and determine which interaction is responsible for the observed failure.

suppose system is like:
A,D then B then C
and the system fails.

The learner must determine whether the problem is:
- A to B
- B to C 
- D to B
- or some interaction among them.
    

This requires **causal discrimination**.

### Example from programming

> Analyze this program and determine why it produces a memory leak under repeated execution.

The learner may need to examine:
- object creation
- references
- object lifetime
- garbage collection behavior
    

and determine which structural relationship causes the observed problem.

### Characteristics
Number of elements:        several
Relationship count:        multiple
Interdependence:           high
Causal reasoning:          high
Ambiguity:                 moderate/high
Competing explanations:    possible
Evidence integration:      substantial

The key difference from Analyze level 3 is:

### Analyze 3

> How do these things interact?

### Analyze 4

> Which interaction or structural feature explains this particular outcome?

So the learner moves from **relationship mapping** toward **causal or structural diagnosis**.

# Analyze: difficulty level 5 — Complex system analysis

## Definition

The learner must analyze a complex, interdependent system containing multiple components, relationships, constraints, and possibly competing explanations.

The learner may need to:
1. decompose the system,
2. identify relevant components,
3. determine multiple relationships,
4. distinguish relevant from irrelevant factors,
5. trace causal pathways,
6. account for constraints,
7. compare competing explanations,
8. determine the most plausible explanation based on available evidence.
    
The overall structure may look like:
A \to B \to C \to F \to E \to D \to A AND B \to E 
while there's constraint 1 between B and C and constraint 2 between D and E and there's an observed outcome between E and f
The learner must make sense of the structure as a whole.

### Example

> Analyze the interaction between A, B, C, and D under the given constraints and determine the most likely cause of the observed behavior, using the available evidence.

The difficulty does **not** come merely from having more components.

It comes from:
- interdependence
- multiple possible causal pathways
- constraints
- ambiguity
- competing explanations
- evidence interpretation
    
### Example from computer science

> A distributed application experiences intermittent latency spikes. Given the request traces, database metrics, network latency measurements, cache behavior, and concurrency patterns, analyze the system and determine the most likely source of the bottleneck.

The learner must investigate several possible explanations:
```text
Latency spikes cause:
- Database?
- Network?
- Cache?
- Lock contention?
- Interaction between components?
The learner has to determine which explanation best accounts for the evidence.

### Characteristics
Number of elements:        many
Relationship count:        many
Interdependence:           high
Causal depth:              multi-step
Ambiguity:                 high
Constraints:               multiple
Competing explanations:    multiple
Evidence integration:      high
Structural complexity:     high



|Level|Primary cognitive demand|
|---|---|
|**Analyze 1**|Decompose a whole into meaningful parts|
|**Analyze 2**|Determine individual relationships between parts|
|**Analyze 3**|Determine how multiple relationships interact|
|**Analyze 4**|Identify causal or structural factors explaining an outcome|
|**Analyze 5**|Integrate evidence to analyze a complex system with constraints and competing explanations|

---

# What should actually increase Analyze difficulty?
The follwing dimensions along which difficulty should increase.

## 1. Number of relevant elements
Analyze level 1 = Few elements
Analyze level 2 = Few elements with relationships
Analyze level 3 = Several interacting elements
Analyze level 4 = Several elements with causal structure
Analyze level 5 = Many interacting elements


However:
> **More elements alone do not automatically mean greater analytical difficulty.**

Ten independent components can be easier to analyze than three tightly coupled components.

## 2. Relationship complexity

Analyze level 1 → Part-whole structure
Analyze level 2 → Direct relationship
Analyze level 3 → Multiple relationships
Analyze level 4 → Causal/conditional relationships
Analyze level 5 → Interdependent, feedback, or multi-step causal relationships


## 3. Interdependence

This is particularly important.

Compare:
A \to B
C \to D
E \to F


These relationships are mostly independent.

Now compare:
A \to B
B \to C
C \to D
D \to A
Now changing one component may affect several others.

The second structure is more analytically difficult even if it contains fewer elements.
## 4. Causal depth

Analyze level 2:
A \to B

Analyze level 3:
A \to B \to C

Analyze level 4:
A,D \to B \to C


Analyze level 5:
A \to B \to C \to F \to E \to D \to A  AND also B \to E
As causal pathways become longer and more interconnected, analytical difficulty increases.

## 5. Ambiguity and competing explanations

At low difficulty:
One structure
One obvious relationship


At high difficulty:
Observed outcome
- Possible explanation A
- Possible explanation B
- Possible explanation C

The learner must determine which structure or explanation best fits the available information.

This is a major source of Analyze difficulty.

## 6. Evidence integration

Analyze 5 may require combining information from multiple sources:

- a graph
    
- a table
    
- a system description
    
- observed behavior
    
- constraints
    
- measurements
    

The learner must determine how these pieces fit together.

However, simply giving the learner more information is not enough.

The information must actually need to be **structurally integrated**.

Otherwise, it is just unnecessary information load.


# A critical boundary: Analyze vs Apply

This is probably the most important distinction

### Apply

> Given these values, use formulas A, B, and C to calculate the final result.

Even if it has ten steps, this may still be Apply.

Why?

Because the learner already knows:
Step 1 requires Formula A
Step 2 requires Formula B
Step 3 requires Formula C

The primary task is using procedures.

### Analyze

> Given the behavior of the system, determine which of the relationships between A, B, and C explains the observed result.

Here the learner must **determine the structure or causal explanation**.

### So:

Apply:
Known structure \to execute procedures \to answer

Analyze:
Given information \to determine structure/relationships/causes


This distinction is more useful than simply saying:

> "Analyze has more steps than Apply."

It does not. A 20-step procedural calculation can still be Apply.

---

# Analyze vs Understand

Another important distinction:

### Understand

> Explain how a binary search tree maintains ordering.

The conceptual model is already known.

### Analyze

> Examine this tree and determine which nodes violate the binary search tree ordering property.

Now the learner must inspect the presented structure and determine where the relevant relationships occur.

So:
Understand:
Explain the known structure.

Analyze:
Examine a specific structure and determine its organization, relationships, patterns, or violations.

# Analyze vs Evaluate
### Analyze

> Determine which factor most likely caused the performance degradation.

The learner determines the causal explanation.

### Evaluate

> Determine which of these two proposed solutions is better for preventing future performance degradation and justify your judgment using performance, cost, and maintainability criteria.

The learner is making a **judgment according to criteria**.

So:
Analyze:
What is happening, and why?

Evaluate:
Which option, claim, or solution is better, more valid,
more appropriate, or more justified?


A complex Analyze question may involve evidence, but it does not automatically become Evaluate.

---

# What should NOT artificially increase Analyze difficulty?
Do not make it harder merely by:
- making the passage longer;
- adding irrelevant facts;
- using obscure terminology;
- requiring excessive calculations;
- requiring arbitrary amounts of information to be memorized
- making the wording intentionally confusing.
    
Those may make a question frustrating without increasing its intended analytical complexity.

Difficulty should come from:

> **the structure that must be discovered or interpreted.**

That is the central principle of Analyze.
""".strip()

EVALUATE_DIFFICULTY_TEXT="""
The central question is usually something like:

> Which option is better, more appropriate, more effective, more valid, or more justified—and why?

definition:

> **Evaluate questions require the learner to make and justify a judgment about the quality, validity, appropriateness, effectiveness, or relative value of an idea, claim, method, solution, design, argument, or alternative. The judgment should be based on relevant criteria, evidence, standards, requirements, or trade-offs. Difficulty increases through the number and complexity of criteria, amount and ambiguity of evidence, number of alternatives, degree of conflict between criteria, uncertainty, and the need to justify a judgment despite the absence of a single objectively obvious answer.**

# what makes something an Evaluate question?

A question is not Evaluate merely because it asks:

> "Which one is better?"

The learner must actually make a **judgment against some basis**.

For example:

### Not necessarily Evaluate

> Which algorithm has lower time complexity?

If this is simply asking the learner to retrieve or calculate a known property, it may be Remember, Understand, or Apply.

### Evaluate

> Which algorithm is more appropriate for this application, considering execution time and memory limitations?

Now there is a judgment about **appropriateness relative to criteria**.

The learner must decide:
Between options: A VS B VS C ..etc
in terms of:
-  Time performance
- Memory usage
- Application requirements

to reach a Judgment


The key idea is:
> **Evaluation requires a conclusion about value, quality, suitability, or preference, supported by a basis for that conclusion.**

---
# Evaluate: difficulty level 1 — Simple judgment using one obvious criterion

## Definition
The learner must make a relatively straightforward judgment using **one dominant criterion**, where the criterion is obvious and the available information strongly supports one answer.

### Example
> Which algorithm is faster for this input?

Suppose that they find that:
Algorithm A: O(n)
Algorithm B: O(log n)

then answer becomes B

For a sufficiently large input, the criterion is clear:
Criterion: Execution time
then they Compare: A and B
conclude: Algorithm B

The learner makes a judgment, but there is little ambiguity.

### Other examples
> Which of these two designs uses less memory?
> Which source is more reliable based on publication date?
> Which implementation is more efficient according to the given execution times?

### Characteristics
Criteria:                1
Alternatives:            usually 2
Evidence complexity:     low
Ambiguity:               low
Trade-offs:              none/minimal
Justification burden:    low

### Important distinction

At this level, the learner may still need to provide a brief reason:

> Algorithm B is preferable because it has a lower execution time.

But they do not need to reconcile competing considerations.

The structure is:
- One criterion

- Compare alternatives
- reach Obvious judgment

# Evaluate: difficulty level 2 — Explicit criterion with justification

## Definition

The learner is given or expected to use a **specific evaluative criterion**, but must explicitly justify the judgment using relevant evidence or reasoning.

The difference from Evaluate 1 is that the learner is not just selecting an answer. They must show:

> **Why does this option satisfy the criterion better?**

### Example

> Which algorithm is more memory-efficient? Justify your answer.

The criterion is explicit: Memory efficiency


The learner examines relevant evidence:
Algorithm A and finds it's O(n) memory
Algorithm B and finds it's O(log n) memory

Then concludes:
> Algorithm B is more memory-efficient because it requires less memory as input size grows.

### Structure
Given Explicit criterion + Relevant evidence
The learner Compare alternatives, provides a judgement + justification. 

### Characteristics
Criteria:                1
Alternatives:            2 or more
Evidence complexity:     low/moderate
Ambiguity:               low/moderate
Trade-offs:              minimal
Justification burden:    explicit


The main increase in difficulty is:
Evaluate 1:
Make the judgment.

Evaluate 2:
Make the judgment and explicitly defend it using the relevant criterion and evidence.


# Evaluate: difficulty level 3 — Multiple criteria

## Definition
The learner must evaluate one or more alternatives using **several relevant criteria**.

The difficulty comes from having to consider multiple dimensions rather than optimizing for one property.

### Example
> Evaluate these two algorithms in terms of time complexity, memory usage, and implementation complexity.

The learner must construct something like:
|Criterion|Algorithm A|Algorithm B|
|---|---|---|
|Time|Better|Worse|
|Memory|Worse|Better|
|Implementation complexity|Simpler|More complex|

The learner must examine several dimensions.

### Important point
At Evaluate level 3, the criteria do **NOT necessarily need to conflict strongly**.

The learner may simply be asked to evaluate each alternative across multiple dimensions.

For example:
> Evaluate this machine-learning model in terms of accuracy, inference speed, memory consumption, and interpretability.

The task requires multidimensional judgment.

### Characteristics
Criteria:                multiple
Alternatives:            one or more
Evidence complexity:     moderate
Ambiguity:               moderate
Trade-offs:              possible, but not central
Evidence integration:    required
Justification burden:    moderate


# Evaluate: difficulty level 4 — Conflicting criteria and trade-offs

This is where evaluation becomes substantially more difficult.

## Definition
The learner must make a judgment when **improving one criterion worsens another**.

There is no longer necessarily a universally correct answer.

### Example

> Evaluate whether algorithm A or B is more appropriate given requirements for speed, memory usage, maintainability, and scalability.

Suppose:
Algorithm A = Fast + Scalable - High memory use - More complex

Algorithm B = Low memory use + Easier to maintain - Slower
```

Now the learner cannot simply say:

> "A is better."

They must ask:

> Better according to what priorities?

This introduces **trade-offs**.

The learner must weigh competing values.

### The essential feature

A high-quality answer should recognize something like:

> Algorithm A is preferable if performance and scalability are the dominant requirements, whereas Algorithm B may be preferable when memory efficiency and maintainability are more important.

This is genuine evaluation because the learner must make a judgment **conditional on priorities**.

### Characteristics
Criteria:                multiple
Criteria conflict:       high
Alternatives:            multiple
Evidence complexity:     moderate/high
Ambiguity:               moderate/high
Trade-offs:              central
Prioritization:          required
Justification burden:    high


The progression from Evaluate 3 to Evaluate 4 is:
Evaluate 3:
Consider multiple criteria.

Evaluate 4:
Consider multiple criteria that cannot all be optimized simultaneously.


That distinction is important for your prompt.

# Evaluate: difficulty level 5 — Complex judgment under uncertainty

This is the highest difficulty level.

## Definition

The learner must make and defend a judgment when the situation contains:
- multiple criteria;
- conflicting requirements;
- incomplete or ambiguous evidence;
- uncertainty;
- multiple plausible alternatives;
- competing stakeholder priorities;
- constraints;
- no clearly optimal solution.
    

The learner must not simply identify trade-offs.

They must determine:

> **Given these trade-offs and uncertainties, what judgment is most justified?**

### Example
> Evaluate the proposed architecture given the performance measurements, scalability requirements, operational constraints, and conflicting stakeholder requirements. Identify the trade-offs and justify whether the architecture should be adopted.

The learner may need to consider:
- Performance
- Architecture
- Scalability
- Cost
- Maintainability
- Operational risk
- Stakeholder priorities

then reaches a Judgment


But the evidence may not point perfectly in one direction.
For example:

Performance = supports adoption
Scalability = supports adoption
Cost        = argues against adoption
Complexity  = argues against adoption
Risk        = uncertain


The learner must integrate this information and reach a defensible conclusion.

### Characteristics

Criteria:                many
Criteria conflict:       high
Alternatives:            multiple/plausible
Evidence complexity:     high
Evidence uncertainty:    high
Ambiguity:               high
Constraints:             multiple
Stakeholder conflict:    possible
Trade-offs:              central
Justification burden:    very high

# The important distinction between Evaluate 4 and Evaluate 5
### Evaluate 4

The learner faces **conflicting criteria**.

For example:
Option A:
Fast but expensive

Option B:
Slow but cheap

The learner must decide which trade-off is more appropriate.

The evidence itself may still be relatively clear.

### Evaluate 5

The learner faces:
Conflicting criteria + Uncertain or incomplete evidence + Multiple constraints or stakeholders + Potentially multiple plausible conclusions

For example:
Option A:
Performance: Good
Cost: Unknown long-term
Scalability: Good
Operational risk: Moderate
Maintenance burden: Uncertain

Option B:
Performance: Moderate
Cost: Lower
Scalability: Uncertain
Operational risk: Lower
Maintenance burden: High


There may be no objectively demonstrable "winner."

The learner must produce the **most justified judgment based on the available evidence and assumptions**.

So:

Evaluate 4:
Which trade-off is preferable?

What judgment is most justified despite complex trade-offs and uncertainty?
```

---

# The five-level progression
EVALUATE 1
One obvious criterion

EVALUATE 2
One explicit criterion + evidence-based justification

EVALUATE 3
Multiple criteria

EVALUATE 4
Multiple conflicting criteria requiring trade-offs

EVALUATE 5
Complex judgment involving conflicting criteria, uncertainty, ambiguous evidence, constraints, and multiple plausible conclusions


# What should actually increase Evaluate difficulty?
## 1. Number of criteria
EVALUATE level 1 → One
EVALUATE level 2 → One explicit criterion
EVALUATE level 3 → Multiple
EVALUATE level 4 → Multiple conflicting
EVALUATE level 5 → Multiple conflicting and contextual

## 2. Degree of conflict between criteria

This is more important than simply counting criteria.

Consider:
Criterion A: favors Option A
Criterion B: favors Option A
Criterion C: favors Option A
Even though there are three criteria, the decision may be easy.
Now:

Criterion A: favors Option A
Criterion B: favors Option B
Criterion C: favors Option D,A


This creates genuine evaluative difficulty.

Therefore:

> **Difficulty increases when the criteria produce conflicting conclusions that require prioritization or trade-offs.**

## 3. Evidence complexity

At lower levels:
One clear fact + One conclusion


At higher levels:
Evidence A: supports option A
Evidence B: supports option B
Evidence C: partially supports both
Evidence D: uncertain


The learner must integrate the evidence.

## 4. Uncertainty

Evaluate difficulty can increase when:
- evidence is incomplete;
- measurements have limitations;
- future outcomes are uncertain;
- assumptions are necessary;
- the consequences of different choices are probabilistic.
    

However, uncertainty should be **meaningful**, not artificial.
Do not simply omit necessary information and expect the learner to guess!

Instead, the learner should be able to say:
> Based on the available evidence, Option A is preferable, assuming X is more important than Y.

That is a legitimate high-level evaluation.

## 5. Number of alternatives

More alternatives can increase difficulty:
EVALUATE level 1 & 2: often 2 alternatives
EVALUATE level 3: 2–3 alternatives
EVALUATE level E4: multiple alternatives
EVALUATE level 5: several plausible alternatives
```

But again:

> More alternatives alone do not automatically create higher evaluative difficulty.

Five options that are obviously ranked are easier than two options with deeply conflicting trade-offs.

---

## 6. Justification burden

As difficulty increases, the learner should move from:

E1:
"This is better."

E2:
"This is better because..."

E3:
"This performs better on criteria A and B, but worse on C."

E4:
"The appropriate choice depends on the relative
importance of these competing criteria."

E5:
"Given the available evidence, uncertainty,
constraints, assumptions, and stakeholder priorities,
this option is the most justified, although the conclusion
would change if certain assumptions or priorities changed."


That is a meaningful progression in evaluative reasoning.

# A critical distinction: Evaluate vs Analyze

This distinction is essential.

### Analyze

> Determine which component caused the system failure.

The learner determines:

> What happened, and why?

### Evaluate

> Determine which proposed solution is most appropriate for preventing future failures, considering cost, reliability, maintainability, and performance.

The learner determines:

> Which option should be preferred, and why?

So:
ANALYZE
Determine structure, relationships, causes, patterns.

EVALUATE
Make a judgment using criteria and evidence.


Even if an Evaluate question requires analysis first, its **final and primary cognitive operation** is judgment.

For example:
> Analyze the failure data and evaluate which solution should be adopted.

This actually contains multiple Bloom operations.
If you classify it as Evaluate, the final task should be the judgment:

# Evaluate vs Apply

### Apply
> Use the decision matrix to calculate the weighted score of each option.

This is primarily procedural.

### Evaluate

> Determine which option should be selected based on the decision criteria and justify whether the weighting appropriately reflects the system requirements.

Now the learner makes a judgment.

The distinction:
Apply:
Use a decision method.

Evaluate:
Judge the options or the appropriateness of the decision.

# Evaluate vs Create

### Evaluate

> Evaluate which database architecture is most appropriate for these requirements.

The learner judges existing alternatives.

### Create

> Design a database architecture that satisfies these requirements.

The learner generates a new solution.

Of course, real creation often includes evaluation, but the target cognitive operation differs.

---

# What should NOT artificially increase Evaluate difficulty?

Your prompt should explicitly prohibit:
- adding irrelevant criteria;
- providing excessive irrelevant evidence;
- making terminology obscure;
- making wording vague;
- withholding information necessary to make any defensible judgment;
- increasing answer length without increasing evaluative complexity.

For example:

> Evaluate this algorithm using 20 irrelevant metrics.

is not necessarily Evaluate 5.

Likewise:

> Which algorithm is better?

without defining any context may simply be poorly specified.

High-level evaluation requires **meaningful criteria and contextual constraints**, not arbitrary ambiguity.
""".strip()

CREATE_DIFFICULTY_TEXT="""
The defining feature of the **'Create'** level is not simply that the answer is long, complicated, or technically advanced. The defining cognitive operation is:

> **The learner must construct, generate, design, plan, or produce a coherent new artifact, solution, model, strategy, or system by organizing and integrating knowledge.**

The five difficulty levels should then describe **how demanding that act of creation is**.

---

# The central principle

For Create questions:

> **Difficulty increases according to the complexity of what must be created, the number and interaction of requirements, the amount of knowledge that must be integrated, the severity of constraints, the openness of the design space, and the amount of justified decision-making required.**

# First: what actually makes a Create question "Create"?

Consider:

> Implement the binary search algorithm.

This may be **Apply** if the student is simply reproducing a known algorithm or following a known procedure.

Now consider:

> Design a search component for an application with static data, frequently updated data, different query patterns, and latency constraints.

This is clearly more like **Create**, because there is no single procedure to execute. The learner must construct a solution.

So a useful distinction is:
Apply = Use an existing procedure or method.

Create = Construct or organize a solution, artifact, plan, or design by making decisions about how the parts should be arranged.

##### Create does **not necessarily mean inventing something completely original**.
A student can create a program, design, experiment, model, or architecture that already exists elsewhere.

The important question is:

> Does the learner have to **construct the solution themselves** by organizing knowledge into a coherent whole?

# Create: difficulty level 1 — Straightforward production

## Definition

The learner produces a relatively simple artifact with a **clear goal and limited design space**.

The task may still allow some choice, but there are few requirements and little need to balance competing constraints.

### Example

> Write a function that calculates the factorial of a number.

The artifact is being created, but:

- there is one primary goal
    
- few components are involved
    
- constraints are minimal
    
- the solution structure is relatively straightforward
    

### Characteristics
Artifact scope:         small
Primary goals:          1
Requirements:           few
Concept integration:    low
Constraints:            minimal
Trade-offs:             none/minimal
Design freedom:         limited


### Important distinction
A Create 1 task should still involve **production or construction**, not merely execution.

For example:

> Use this formula to calculate 5!.

That is Apply.

But:

> Create a small program that calculates factorials.

can be Create because the learner must construct an artifact.

The boundary can depend on context. If students are simply reproducing a template they were explicitly taught, it may still function more like Apply.

---

# Create: difficulty level 2 — Multiple explicit requirements

## Definition

The learner must create an artifact that satisfies **several clearly specified requirements**.

The requirements are still relatively independent and explicit.

### Example

> Implement a factorial function that:
> 
> 1. calculates factorials,
>     
> 2. rejects negative numbers,
>     
> 3. handles invalid input, and
>     
> 4. documents its behavior.
>     

Now the learner has to construct an artifact satisfying multiple conditions:


The learner has more to coordinate than in Create 1.

However, the requirements are still largely explicit:

> "Your solution must do A, B, C, and D."

The student does not necessarily need to discover the major constraints themselves.

### Characteristics

Artifact scope:         small/moderate
Primary goals:          1
Requirements:           multiple and explicit
Concept integration:    low/moderate
Constraints:            explicit
Trade-offs:             limited
Design freedom:         moderate


### The main source of difficulty

The difficulty comes from:

> **Requirement satisfaction**

The learner must ensure that the created artifact fulfills multiple stated conditions.

---

# Create: difficulty level 3 — Multi-concept integration

## Definition

The learner must create something that requires **integrating several different concepts, methods, or components into one coherent whole**.

This is the important shift.

Create 2 might involve: One main concept + Several requirements

Create 3 involves: MULTIPLE concepts producing an Integrated artifact
```

### Example

> Design a module that calculates factorials, validates input, handles errors, and provides unit tests.

The learner may need to integrate: Algorithmic logic + Input validation + Error handling + Module design + Testing Coherent producing a software component

The challenge is no longer simply:

> "Did I satisfy requirement A, B, and C?"

It is also:

> "How should these different concepts and components be organized so they work together?"

### Characteristics
Artifact scope:         moderate
Primary goals:          multiple related goals
Requirements:           multiple
Concept integration:    substantial
Constraints:            moderate
Trade-offs:             some
Design freedom:         moderate/high


### Another example

For biology:

> Design an experiment to investigate how temperature and pH independently and jointly affect enzyme activity.

The learner must integrate:
- experimental design
- independent variables
- dependent variables
- controls
- measurement
- interpretation
    

into one coherent experimental structure.

That is Create 3 because multiple concepts must be synthesized into a working design.

---

# Create: difficulty level 4 — Design under interacting constraints

## Definition

The learner must construct a solution while dealing with **multiple constraints that interact with each other**.

This is where trade-offs become important.

### Example

> Design a factorial service that supports:
> 
> - concurrent requests,
>     
> - input validation,
>     
> - failure handling,
>     
> - predictable and good performance.
>     

The difficulty is not just:

> "Include A, B, C, and D."

The learner may need to consider interactions:
- Concurrency
- Performance
- Resource usage
- Failure handling

Improving one property might affect another.

For example:
- increasing concurrency may increase resource consumption
- extensive validation may affect performance
- failure recovery may increase complexity
- caching may improve speed but introduce consistency concerns
    

The learner therefore has to make **design decisions under constraints**.

### Characteristics
Artifact scope:         moderate/large
Requirements:           multiple
Constraints:            interacting
Concept integration:    high
Trade-offs:             significant
Design freedom:         high
Decision justification: often required
### The important difference from Create 3

Create 3:
> Integrate several things into a coherent solution.

Create 4:
> Integrate several things **while managing conflicts and constraints between them**.

This is the transition from simple synthesis toward genuine design.

---

# Create: difficulty level 5 — Open-ended, complex design

## Definition

The learner must create a solution for a complex problem where:
- there are many interacting requirements
- constraints may conflict
- there may be multiple valid solutions
- the solution structure is not predetermined
- the learner must make significant design choices
- the learner may need to establish priorities or assumptions
- major decisions should be justified
    

### Example

> Design an architecture for a distributed computation service that supports arbitrary mathematical operations, horizontal scaling, fault tolerance, request prioritization, observability, and backward-compatible API evolution. Justify the major architectural decisions.

This requires integrating:
Distributed systems + Scalability + Fault tolerance + API design + Scheduling/prioritization + Observability + Backward compatibility
then produce an Architecture


But these requirements also interact:
Scalability against Consistency
Fault tolerance against Complexity
Performance against Observability overhead
Backward compatibility against Design flexibility
Prioritization against Fairness


There may be no single objectively correct architecture.

The learner must therefore:
1. interpret the problem
2. determine important design concerns
3. organize components
4. make architectural decisions
5. manage trade-offs
6. justify those decisions
7. produce a coherent overall solution
    

### Characteristics
Artifact scope:         large/complex
Requirements:           numerous
Constraints:            interacting/conflicting
Concept integration:    very high
Trade-offs:             substantial
Design freedom:         very high
Solution uniqueness:    low; multiple valid solutions
Decision justification: essential
Uncertainty:            often present

# The difference between explicit requirements and constraints

This distinction is particularly useful for your prompt.

Suppose you ask:

> Create a function that:
> 
> - calculates factorials,
>     
> - validates input,
>     
> - handles errors.
>     

Those are mostly **requirements**.

The student can think:
Requirement 1 = implement it
Requirement 2 = implement it
Requirement 3 = implement it


Now consider:

> Design a service that must maintain low latency while processing large workloads using limited computational resources.

These are **constraints** that interact:
Low latency interacts with Large workload interacts with Limited resources
```

You cannot necessarily optimize everything simultaneously.

The learner has to make trade-offs.

This distinction is useful:

> **Requirements specify what the solution must achieve.**

> **Constraints limit how the solution can achieve it.**

Create difficulty increases significantly when requirements and constraints begin to **interact and conflict**.

---

# The difference between Create 4 and Create 5
### Create 4
The problem structure is mostly defined.
The learner is given:
Problem + Requirements + Constraints
and must design a solution within that structure.

### Create 5

The problem is more open-ended.

The learner may need to determine:
- which requirements are most important
- which constraints should take priority
- what assumptions are reasonable
- what architecture or strategy should be used
- how conflicting objectives should be balanced
    

In other words:
Create 4:
"Design a solution satisfying these constraints."

Create 5:
"Design a solution to this complex problem, while determining and justifying the major structure and trade-offs of the solution."


Create 5 involves more **design-space exploration**.

There are more plausible paths to a solution.

---

# A useful model for Create difficulty

You can think of Create difficulty as being influenced by these dimensions:
f(R, I, C, T, O, J)  
where:
- (R) = number and complexity of **requirements**
- (I) = **concept integration**
- (C) = complexity and interaction of **constraints**
- (T) = number and severity of **trade-offs**
- (O) = **openness** of the design space    
- (J) = amount of **independent judgment** required
    

The levels roughly progress like this:

|Dimension|C1|C2|C3|C4|C5|
|---|---|---|---|---|---|
|Requirements|Few|Multiple|Multiple|Many|Numerous/interacting|
|Integration|Low|Low–moderate|High|High|Very high|
|Constraints|Minimal|Explicit|Moderate|Interacting|Interacting/conflicting|
|Trade-offs|None|Minimal|Some|Significant|Major|
|Openness|Low|Low–moderate|Moderate|High|Very high|
|Independent judgment|Low|Low|Moderate|High|Very high|

These should be treated as **guidelines**, not strict numerical thresholds.

A Create 5 question does NOT need to score maximum on every dimension. What matters is the overall level of design complexity.

---

# What should NOT make a Create question harder?
## 1. Longer output

A 2,000-word answer is not automatically Create 5.
A learner could write an unnecessarily long Create 1 solution.
---
## 2. Arbitrary extra requirements
The additional requirements should create a genuine design problem.
## 3. Obscure domain knowledge

A Create question should not become Create 5 simply because it requires knowledge of a highly obscure API or fact.

For example:

> Design a program using this obscure library.

That may simply test Remember.

Create difficulty should come primarily from the **act of constructing and organizing the solution**.

## 4. Multiple unrelated tasks
This:

> Create a program, explain photosynthesis, calculate a derivative, and list five historical events.
is not Create 5.

It is just multiple unrelated tasks.
Create difficulty should involve:

> **integration into one coherent artifact or solution.**

---

# Boundary: Create vs Apply
### Apply

> Implement Dijkstra's algorithm.

If the student has learned the algorithm and simply executes the known procedure, this is primarily Apply.

### Create

> Design a routing strategy for a network where edge costs change dynamically and some nodes have reliability constraints.

Now the student must decide:
- what approach to use
- how to structure it
- how to handle the constraints
- how components interact
    

That is Create.

A useful rule is:

> **If a correct response can primarily be produced by following a known procedure or template, it is more likely Apply. If the learner must organize, synthesize, or design the structure of the solution, it is more likely Create.**

# Boundary: Create vs Evaluate

These two often overlap.

Consider:

> Evaluate these three architectures and determine which one is best.

Primary operation:Evaluate

Now:

> Evaluate these architectural options, then design a new architecture that combines appropriate elements from them to satisfy the system requirements.

Now the final primary operation is: Evaluate, then decision informs, then Create
The task may involve both.

For classification purposes, classify according to the **primary intended learning objective**.

If the main outcome is a judgment:

> Evaluate.

If the main outcome is a constructed solution:

> Create.
""".strip()


MSQ_TEXT="""
# Multiple-Select Question (MSQ) Specification
## 1. Definition

An **MSQ**, or Multiple-Select Question, presents a question stem followed by multiple answer choices where:

> **More than one option may be correct, and the learner must select all options that satisfy the condition stated in the stem.**

Unlike a standard single-answer MCQ, the learner cannot assume that exactly one answer is correct.

The item tests not only whether the learner can recognize correct information, but also whether they can:
1. evaluate each option independently against the stem,
2. distinguish correct options from incorrect or partially correct alternatives,
3. avoid selecting plausible distractors,
4. identify the complete set of answers satisfying the question.
    

The fundamental response structure is:

```text
Stem

Select all that apply:
[A] Option A
[B] Option B
[C] Option C
[D] Option D
[E] Option E
```

For example:

> **Which of the following are characteristics of a mammal? Select all that apply.**
> [A] Has hair or fur  
> [B] Produces milk for offspring  
> [C] Is an endothermic vertebrate  
> [D] Must lay eggs  
> [E] Has mammary glands
then then answer is  in the form of the corresponding letters: (B,C,E)

# 2. Core design principle

An MSQ should not be just:

> "An MCQ with several correct answers."

That is mechanically true, but educationally incomplete.

A well-designed MSQ should have a clear **selection criterion**.

The learner should be able to evaluate every option according to the same underlying question.

For example:

> Which of the following are renewable energy sources?

The selection criterion is:
Is this energy source renewable?


Where each option can independently be evaluated against that criterion.

This is preferable to a heterogeneous question such as:

> Which of the following statements about biology are correct?

if the options test unrelated facts.

A good MSQ should generally have:
- One coherent question
- One primary selection criterion
- Multiple independently evaluable options
```

---

# 3. question structure

Every MSQ should contain the following components.

## 3.1 Stem

The stem must clearly state:

- what the learner is evaluating,
    
- what criterion determines correctness,
    
- what action the learner must perform.
    

Recommended format:

> **Which of the following [objects/statements/processes/etc.] satisfy [criterion(s)]? Select all that apply.**

Examples:

> Which of the following are examples of symmetric encryption algorithms? Select all that apply.

> Which statements correctly describe natural selection? Select all that apply.

> Which expressions evaluate to `true`? Select all that apply.

> Which factors can increase the rate of a chemical reaction? Select all that apply.

## 3.2 Selection instruction

The question must explicitly communicate that multiple answers may be selected.

Use one of the following wordings:
- Select all that apply.
- Select all correct answers.
- Choose all options that satisfy the stated condition.

## 3.3 Answer options

Each option should be:
- independently evaluable,
- relevant to the stem,
- grammatically compatible with the stem,
- reasonably similar in style and length,
- unambiguous under the intended curriculum,
- clearly correct or incorrect according to the stated criterion.
    

Avoid options that are:
- irrelevant,
- trivially absurd(wrong in an obvious way),
- grammatically inconsistent,
- dependent on another option,
- ambiguous because of missing conditions,
- duplicates or near-duplicates,
- unintentionally correct.
    
# 5. Global constraints for all MSQs

These constraints should apply regardless of difficulty level.

## 5.1 There must be multiple correct answers

An MSQ must contain at least: 2 correct options

The exact number should not be used as the primary difficulty mechanism.
## 5.2 Every option must be independently evaluable

The learner should be able to evaluate:
Option A: correct or incorrect
Option B: correct or incorrect
Option C: correct or incorrect
without needing to select another option first.

CRITICAL: Avoid this type of choices(where a choice represents other chocies):
> A. Both B and C  
> B. X  
> C. Y

This creates option dependency.

Also avoid:

> A. Statement 1 is correct and Statement 2 is incorrect.

Avoid "all of the above" and "none of the above"

Do not use:
- All of the above
- None of the above
- Both A and C
- A, B, and D only

## 5.4 The correctness criterion must be stable

The same criterion should apply to every option.

Good:

> Which of the following are examples of renewable energy sources?

Every option is tested against: "Is this renewable?"

Poor:

> Which of the following statements about energy are correct?

Possible options might test:
- definitions,
- causes,
- calculations,
- historical facts.
    

This produces an incoherent item.

---

## 5.5 Avoid trivial distractors

Bad:
> Which of these are mammals?
> [ ] Dog  
> [ ] Cat  
> [ ] Whale  
> [ ] Rectangle  
> [ ] JavaScript

'JavaScript' & 'Rectangle' distractors are OBVIOUS to be wrong without needing to study anything.

A distractor should be:
> **plausible to a learner who has incomplete, superficial, or partially incorrect understanding of the target knowledge.**

For example:
> Which are mammals?
> 
> [ ] Dolphin  
> [ ] Shark  
> [ ] Bat  
> [ ] Penguin  
> [ ] Whale

'Shark' & 'Penguin' distractors are educationally meaningful because common misconceptions may exist
- All options have similalirty that they all are animals, but the question asks specifically about "mammals"

---

## 5.6 Avoid accidental correctness

The model must verify & justify every option.

## 5.7 Avoid "partially correct" options unless explicitly required

For standard MSQs, each option should ideally be classifiable as either:
- Correct

- Incorrect

Avoid:

> Python supports object-oriented programming but cannot support functional programming.

This is problematic because part of the statement is correct and part is false.

Instead:

> Python supports object-oriented programming.

or:

> Python supports functional programming.

If nuanced statements are necessary, the stem must define the condition precisely enough that correctness is objectively determined.

---

# 6. MSQ difficulty: a separate 3-level scale

The three levels below measure the difficulty introduced specifically by the **selection/discrimination structure of the MSQ**.

They are independent from:
- Bloom level,
- Difficulty per Bloom level (the 5 levels stated before)
- concept difficulty,
    
# MSQ Difficulty 1 — Direct recognition

## Definition

MSQ Difficulty 1 requires the learner to identify multiple options that **clearly satisfy a familiar criterion**.
It has 4 to 6 options.
Correct options should be clear examples of the target category, while incorrect options should be meaningfully related but relatively easy to distinguish.

The difficulty comes from:

> evaluating multiple options,

not from subtle conceptual distinctions.

### Core characteristics
Selection criterion:      clear and direct
Conceptual overlap:       low
Distractor plausibility:  low to moderate
Ambiguity:                none
Fine distinctions:        minimal
Option discrimination:    straightforward

The learner should think:
> "Does this obviously belong to the category?"

rather than:

> "This is almost correct, but there is one subtle condition that makes it incorrect."

---

## Example: Biology

> **Which of the following are mammals? Select all that apply.**
> 
> [ ] Shark  
> [x] Dolphin  
> [x] Bat  
> [ ] Penguin  
> [x] Elephant

The learner evaluates category membership.

The distractors are related to animals but do not require subtle distinctions.

---

## Example: Mathematics

> **Which of the following numbers are prime? Select all that apply.**
> 
> [x] 2  
> [ ] 4  
> [x] 7  
> [ ] 9  
> [x] 13

The criterion is clear: Does the number have exactly two positive divisors?


---

## Example: Computer Science

> **Which of the following are programming languages? Select all that apply.**
> 
> [x] Python  
> [x] Java  
> [ ] PostgreSQL  
> [ ] Git  
> [x] Rust

The distractors are relevant to computing but clearly belong to different categories.

---

## Example: History

> **Which of the following were civilizations of the ancient world? Select all that apply.**
> 
> [x] Ancient Egypt  
> [x] Mesopotamia  
> [x] Ancient Greece  
> [ ] The European Union  
> [ ] The Industrial Revolution

---

## Generation rules for MSQ 1

Generate an MSQ where:

1. the stem defines one clear selection criterion;
    
2. correct options are relatively direct examples;
    
3. distractors are relevant but clearly fail the criterion;
    
4. correctness does not depend on subtle exceptions;
    
5. the learner does not need to compare options against one another;
    
6. each option can be classified using relatively direct knowledge.
    

### Do not create MSQ 1 by:
- making the topic easier,
- making the correct answers obvious through wording,
- using absurd distractors.
    

The difficulty should still come from the MSQ structure, just with straightforward discrimination.

---

# MSQ Difficulty 2 — Meaningful discrimination

## Definition

MSQ Difficulty 2 requires the learner to distinguish between **plausible alternatives that share meaningful similarities with the correct answers**.
It has 6 to 8 options.

Incorrect options should not be obviously unrelated.

Instead, they should represent:

- common misconceptions,
    
- related concepts,
    
- near-category members,
    
- conditions where a rule does not apply,
    
- superficially similar cases.
    

The learner must understand the selection criterion sufficiently to distinguish:
Actually satisfies criterion vs. Looks like it might satisfy criterion

## Core characteristics

Selection criterion:      clear but conceptually meaningful
Conceptual overlap:       moderate
Distractor plausibility:  moderate/high
Misconceptions:           often used
Fine distinctions:        some
Option discrimination:    requires understanding


The learner should need to think:

> "This is related to the concept, but does it actually satisfy the stated condition?"



## Example: Biology

> **Which of the following are produced directly during cellular respiration in eukaryotic cells? Select all that apply.**
> 
> [x] ATP  
> [x] Carbon dioxide  
> [ ] Oxygen  
> [x] Water  
> [ ] Glucose

The distractors are all strongly related to respiration, but not all satisfy the criterion.

## Example: Mathematics

> **Which of the following functions are linear? Select all that apply.**
> 
> [x] (f(x) = 3x + 2)  
> [ ] (f(x) = x^2 + 1)  
> [x] (f(x) = -x)  
> [ ] (f(x) = 1/x)  
> [ ] (f(x) = 2^x)

The learner must distinguish linear functions from other mathematical functions.

## Example: Computer Science

> **Which of the following operations can change the state of a mutable object? Select all that apply.**
> 
> [x] Modifying one of its fields  
> [x] Adding an element to an internal list  
> [ ] Reading one of its fields  
> [ ] Comparing it with another object  
> [x] Removing an element from an internal collection

The incorrect options are conceptually related operations.

---

## Example: Psychology

> **Which of the following are examples of negative reinforcement? Select all that apply.**
> 
> [x] Removing an unpleasant alarm when a person fastens a seat belt  
> [ ] Giving a student praise for completing homework  
> [x] Stopping an irritating sound when the correct action is performed  
> [ ] Taking away a privilege after misconduct  
> [ ] Giving a reward for desired behavior

This requires distinguishing:
Negative reinforcement vs. Positive reinforcement vs. Punishment
```

The distractors target common conceptual confusion.

---

## Generation rules for MSQ 2

Generate an MSQ where:

1. correct and incorrect options belong to the same broad conceptual area;
    
2. distractors are plausible to someone with incomplete understanding;
    
3. at least some distractors should represent common misconceptions or near misses;
    
4. the learner must understand the defining criterion, not merely recognize vocabulary;
    
5. options should differ in a conceptually meaningful way.
    

The model should ask:

> Would a learner who only memorized superficial facts be likely to select this distractor?

If yes, the distractor may be useful.

---

# MSQ Difficulty 3 — Fine-grained discrimination

## Definition

MSQ Difficulty 3 requires the learner to distinguish among **closely related, highly plausible, or conditionally valid alternatives**.
Has 6 to 8 options. Unlike the other two, can have multiple criterions. 
The correct and incorrect options may share most of their conceptual structure.

The learner must attend to:
- precise definitions,
- conditions,
- scope,
- exceptions,
- boundary cases,
- necessary versus sufficient conditions,
- subtle distinctions between related concepts.
    

The difficulty comes from **precision of conceptual discrimination**, not from making the wording intentionally tricky.

This is crucial:

> **MSQ 3 must be conceptually demanding, not linguistically deceptive.**
## Core characteristics
Selection criterion:      precise
Conceptual overlap:       high
Distractor plausibility:  high
Conditions/exceptions:    often relevant
Fine distinctions:        substantial
Option discrimination:    precise conceptual judgment

The learner should think:

> "This is very similar to the correct cases, but does it satisfy the criterion under the exact conditions stated?"

---

## Example: Biology

> **Which statements about natural selection are correct? Select all that apply.**
> [x] Natural selection can change the frequency of heritable traits within a population over generations.
> [ ] Individual organisms evolve genetically during their lifetime because they need to adapt.
> [x] Natural selection requires variation among individuals that can affect reproductive success.
> [ ] Natural selection always produces traits that are optimal in every environment.
> [x] A trait can increase in frequency through natural selection if individuals possessing it tend to leave more offspring under the relevant conditions.

The distractors are highly plausible because they contain concepts associated with evolution but violate precise principles.

---

## Example: Mathematics

> **Which statements are necessarily true for every differentiable function at a point (x=a)? Select all that apply.**
> [x] The function is continuous at (x=a).
> [ ] The function has a local maximum or minimum at (x=a).
> [x] The derivative at (x=a) exists.
> [ ] The derivative at (x=a) must be nonzero.
> [ ] The function must be linear near (x=a).

The learner must distinguish:
Necessary consequence vs. Possible but not necessary consequence


---

## Example: Computer Science

> **Which statements about database transactions with ACID properties are correct? Select all that apply.**
> [x] Atomicity means that a transaction's operations are treated as an all-or-nothing unit.
> [x] Isolation concerns the effects of concurrent transactions on one another.
> [ ] Durability guarantees that a transaction can never be rolled back before it commits.
> [ ] Consistency means that all concurrent transactions execute one at a time.
> [x] A successfully committed transaction should retain its effects despite certain subsequent failures.

The distractors deliberately target precise confusion between the ACID properties.

---

## Example: Physics

> **Under classical mechanics, which statements are necessarily true about an object in equilibrium? Select all that apply.**
> [x] The net force acting on the object is zero.
> [x] The object's acceleration is zero.
> [ ] The object must be stationary.
> [ ] No individual forces can be acting on the object.
> [x] The object may move with constant velocity.

The key distinction is:
Equilibrium ≠ At rest

The learner must understand necessary versus possible properties.
# The MSQ difficulty progression

The three levels can be summarized as:

|Level|Primary difficulty source|Correct vs incorrect options|
|---|---|---|
|**MSQ 1**|Direct recognition|Clearly distinguishable|
|**MSQ 2**|Meaningful discrimination|Plausible, conceptually related|
|**MSQ 3**|Fine-grained discrimination|Highly similar or conditionally distinguishable|


# 9. Distractor construction rules
## MSQ level 1 distractors

Use:

- clearly related but different category members,
    
- common examples of adjacent categories.

## MSQ 2 distractors

Use:

- common misconceptions,
- superficially similar concepts,
- related processes,
- incomplete examples,
- cases where a rule appears relevant but does not apply. 

## MSQ 3 distractors

Use:
- boundary cases,
- necessary/sufficient confusion,
- scope errors, 
- conditional validity, 
- exceptions, 
- conceptually near-identical alternatives,
- technically plausible but incorrect statements.


# 10. Avoid deceptive wording

Do not make MSQ 3 difficult using:

- double negatives,
    
- unnecessary negations,
    
- vague quantifiers,
    
- obscure wording,
    
- grammatical tricks,
    
- inconsistent option phrasing,
    
- hidden assumptions.

# 11. Conditional statements

Conditional statements can be useful, particularly at MSQ 3, but the conditions must be explicit.

Poor:

> Which statements about sorting algorithms are correct?

Better:

> **For comparison-based sorting algorithms in the worst case, which statements are correct? Select all that apply.**

Now the scope is defined.
avoid generating statements whose correctness depends on:
- unspecified implementation details,
- unstated assumptions,
- disputed conventions,
- advanced exceptions outside the curriculum.

# 13. Combining Bloom difficulty with MSQ difficulty

These should remain independent.

For example:

```json
{
  "bloom_level": "understand",
  "task_difficulty": 4,
  "msq_difficulty": 1
}
```

This might involve understanding a relatively complex concept, but the answer options are straightforward to classify.

Conversely:

```json
{
  "bloom_level": "remember",
  "task_difficulty": 2,
  "msq_difficulty": 3
}
```

The underlying knowledge may be relatively simple, but the options are deliberately close and require precise factual discrimination.

For example:

> **Which of the following are valid Java primitive types? Select all that apply.**

Options:
[x] int
[x] boolean
[ ] String
[ ] Integer
[x] double


The distinction between: int vs. Integer
can increase MSQ discrimination difficulty without changing the underlying Bloom level from Remember.

---

# 14. Complete specification summary

## MULTIPLE-SELECT QUESTION (MSQ) FORMAT

An MSQ presents a stem followed by multiple answer options where **two or more options are correct**. The learner must evaluate each option independently and select every option that satisfies the criterion defined by the stem.

### Required structure
```text
Question stem

Select all that apply.

[ ] Option A
[ ] Option B
[ ] Option C
[ ] Option D
...
```

### Stem requirements

The stem must:

1. Clearly state what the learner must evaluate.
    
2. Define one coherent selection criterion.
    
3. Explicitly indicate that multiple answers may be correct using language such as **"Select all that apply."**
    
4. Contain sufficient information to determine whether each option is correct.
    
5. Avoid ambiguity, unnecessary complexity, trick wording, and hidden assumptions.
    

### Option requirements

Each option must:

1. Be independently evaluable as correct or incorrect.
    
2. Be directly relevant to the selection criterion.
    
3. Be unambiguously correct or incorrect under the intended curriculum and stated conditions.
    
4. Be grammatically compatible with the stem.
    
5. Be reasonably similar in style and presentation to other options.
    
6. Avoid depending on another option.
    
7. Avoid "all of the above," "none of the above," "both A and B," or other combination-based answers.
    
8. Avoid arbitrary, absurd, or irrelevant distractors.
    
9. Avoid partially correct statements unless the stem explicitly defines a criterion that makes correctness unambiguous.
    

### Correct answer constraints

1. Include at least **two correct options**.
    
2. Prefer approximately **2–3 correct options if the question has 4 options, 2-5 if the question has 6 options**.
    
3. Vary the number and positions of correct options.
    
4. Do not make the number of correct answers predictable.
    
5. Do not use the number of correct answers as the primary difficulty mechanism.
    

### Recommended option count

Prefer approximately: 4–8 total options
The number of options may vary when educationally justified, but **option count alone must not determine MSQ difficulty**.

## MSQ DIFFICULTY LEVELS

MSQ difficulty is a separate dimension from Bloom level and general task difficulty. It measures the difficulty introduced specifically by the conceptual discrimination required to classify the answer options.

### MSQ Difficulty 1 — Direct Recognition

Require straightforward identification of options that clearly satisfy a familiar and explicit criterion.

Characteristics:

- clear category membership,
    
- low conceptual overlap,
    
- low-to-moderate distractor plausibility,
    
- minimal subtle distinctions,
    
- no important exceptions or boundary cases.
    

Distractors should be relevant but relatively easy to distinguish.

The learner should primarily determine:

> **Does this clearly satisfy the stated criterion?**

Do not define this level merely by using fewer options.

---

### MSQ Difficulty 2 — Meaningful Discrimination

Require discrimination between correct options and plausible, conceptually related distractors.

Characteristics:

- moderate conceptual overlap,
    
- plausible incorrect alternatives,
    
- common misconceptions,
    
- near-category members,
    
- superficially similar cases,
    
- meaningful understanding of the criterion required.
    

The learner should primarily determine:

> **This is related to the concept, but does it actually satisfy the stated criterion?**

Difficulty should arise from meaningful conceptual discrimination rather than obscure wording.

---

### MSQ Difficulty 3 — Fine-Grained Discrimination

Require precise discrimination among highly plausible and closely related alternatives.

Characteristics may include:

- high conceptual overlap,
    
- precise definitions,
    
- boundary cases,
    
- explicit conditions,
    
- exceptions,
    
- scope distinctions,
    
- necessary-versus-sufficient conditions,
    
- technically plausible but incorrect statements,
    
- closely related concepts that differ in important details.
    

The learner should primarily determine:

> **This appears very similar to a correct answer, but under the exact definition, conditions, or scope, does it actually satisfy the criterion?**

Difficulty must come from precise conceptual discrimination, **not linguistic deception**.

Do not use:

- double negatives,
    
- vague wording,
    
- hidden assumptions,
    
- arbitrary exceptions,
    
- grammatical tricks,
    
- unnecessarily complex language.
    

---

## DISTRACTOR DESIGN

Generate distractors according to the MSQ difficulty level.

### MSQ 1 distractors

Use:

- adjacent categories,
    
- related but clearly non-members,
    
- common alternatives that clearly fail the criterion.
    

### MSQ 2 distractors

Use:

- common misconceptions,
    
- superficially similar concepts,
    
- related processes,
    
- incomplete cases,
    
- near misses.
    

### MSQ 3 distractors

Use:

- boundary cases,
    
- conditional cases,
    
- scope errors,
    
- necessary/sufficient confusion,
    
- precise definitional distinctions,
    
- highly plausible but technically incorrect statements.
    

Before finalizing the item, verify every option and write the justification in the JSON. 

Ensure that no distractor accidentally satisfies the criterion and no correct option violates it.

That gives you a cleaner framework than trying to force all difficulty variation into one 1–10 score.
""".strip()

MSQ_SCHEMA="""
very critical: the generated JSON must be a valid JSON.
VERY IMPORTANT AND CRITICAL AND MAJOR DEFNITION OF OUTPUT PERFORMANCE: your output should STRICTLY follow this JSON schema & structure to represent both the question an the answer as the following JSON block: 
### the structure definition: 
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "questions": {
      "type": "array",
      "description": "Array of MSQ (Multiple Select Questions)",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "question_type": {
            "type": "string",
            "enum": ["MSQ"],
            "description": "Question type - currently only MSQ supported"
          },
          "stem": {
            "type": "string",
            "description": "The question text or prompt"
          },
          "options": {
            "type": "array",
            "description": "List of answer options",
            "minItems": 4,
            "items": {
              "type": "object",
              "properties": {
                "id": {
                  "type": "string",
                  "description": "Unique identifier for this option (e.g., 'A', 'B', 'C')"
                },
                "text": {
                  "type": "string",
                  "description": "The option text"
                },
                "correct": {
                  "type": "boolean",
                  "description": "Whether this option is correct"
                },
                "justification": {
                  "type": "string",
                  "description": "Explanation for why this option is correct or incorrect"
                }
              },
              "required": ["id", "text", "correct", "justification"],
              "additionalProperties": false
            }
          },
          "correct_option_ids": {
            "type": "array",
            "description": "IDs of all correct options",
            "minItems": 1,
            "items": {
              "type": "string"
            }
          },
          "bloom_level": {
            "type": "string",
            "enum": ["remember", "understand", "apply", "analyze", "evaluate", "create"],
            "description": "Bloom's Taxonomy cognitive level"
          },
          "task_difficulty": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Difficulty level based on task complexity"
          },
          "msq_difficulty": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3,
            "description": "Difficulty based on number of correct options (1=Easy, 2=Medium, 3=Hard)"
          }
        },
        "required": ["question_type", "stem", "options", "correct_option_ids", "bloom_level", "task_difficulty", "msq_difficulty"],
        "additionalProperties": false
      }
    }
  },
  "required": ["questions"],
  "additionalProperties": false
}
```
### Schema example indicating exactly how you follow the schema structure definition: (very important an must follow the structure)
```JSON
{ 
  "questions": [
    {
      "question_type": "MSQ",
      "stem": "Which of the following are components of the human circulatory system? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Heart",
          "correct": true,
          "justification": "The heart is the central pump of the circulatory system, responsible for propelling blood throughout the body."
        },
        {
          "id": "B",
          "text": "Blood vessels (arteries, veins, capillaries)",
          "correct": true,
          "justification": "Blood vessels form the network of tubes that transport blood to and from all tissues in the body."
        },
        {
          "id": "C",
          "text": "Blood",
          "correct": true,
          "justification": "Blood is the fluid medium that carries oxygen, nutrients, hormones, and waste products throughout the body."
        },
        {
          "id": "D",
          "text": "Lungs",
          "correct": false,
          "justification": "While the lungs are part of the respiratory system and interact with the circulatory system for gas exchange, they are not components of the circulatory system itself."
        },
        {
          "id": "E",
          "text": "Liver",
          "correct": false,
          "justification": "The liver is part of the digestive and excretory systems. Although it filters blood, it is not a primary component of the circulatory system."
        }
      ],
      "correct_option_ids": ["A", "B", "C"],
      "bloom_level": "remember",
      "task_difficulty": 1,
      "msq_difficulty": 2
    },
    {
      "question_type": "MSQ",
      "stem": "Which of the following are characteristics of living organisms? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Cellular organization",
          "correct": true,
          "justification": "All living organisms are composed of one or more cells, which are the basic units of life."
        },
        {
          "id": "B",
          "text": "Ability to reproduce",
          "correct": true,
          "justification": "Reproduction is essential for species survival and is a defining characteristic of life."
        },
        {
          "id": "C",
          "text": "Response to stimuli",
          "correct": true,
          "justification": "Living organisms detect and respond to changes in their internal and external environments."
        },
        {
          "id": "D",
          "text": "Ability to photosynthesize",
          "correct": false,
          "justification": "Only plants, algae, and some bacteria photosynthesize. Not all living organisms have this ability."
        },
        {
          "id": "E",
          "text": "Growth and development",
          "correct": true,
          "justification": "All living organisms grow and undergo developmental changes throughout their life cycles."
        },
        {
          "id": "F",
          "text": "Movement",
          "correct": false,
          "justification": "Not all organisms move actively (e.g., plants, fungi). While movement is common, it is not a universal characteristic."
        },
        {
          "id": "G",
          "text": "Metabolism",
          "correct": true,
          "justification": "All living organisms carry out chemical reactions (metabolism) to maintain life processes."
        }
      ],
      "correct_option_ids": ["A", "B", "C", "E", "G"],
      "bloom_level": "understand",
      "task_difficulty": 2,
      "msq_difficulty": 3
    },
    {
      "question_type": "MSQ",
      "stem": "Which of the following are examples of cellular organelles found in eukaryotic cells? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Nucleus",
          "correct": true,
          "justification": "The nucleus is a membrane-bound organelle that contains the cell's genetic material (DNA)."
        },
        {
          "id": "B",
          "text": "Ribosomes",
          "correct": true,
          "justification": "Ribosomes are responsible for protein synthesis and are found in both eukaryotic and prokaryotic cells."
        },
        {
          "id": "C",
          "text": "Mitochondria",
          "correct": true,
          "justification": "Mitochondria are the powerhouses of eukaryotic cells, generating ATP through cellular respiration."
        },
        {
          "id": "D",
          "text": "Cell wall",
          "correct": false,
          "justification": "Cell walls are found in plant cells, fungi, and some protists, but not in animal cells. They are not universally present in all eukaryotic cells."
        },
        {
          "id": "E",
          "text": "Endoplasmic reticulum",
          "correct": true,
          "justification": "The endoplasmic reticulum (ER) is involved in protein and lipid synthesis, and is part of the endomembrane system."
        },
        {
          "id": "F",
          "text": "Chloroplasts",
          "correct": false,
          "justification": "Chloroplasts are only found in plant cells and some algae. They are not present in all eukaryotic cells."
        },
        {
          "id": "G",
          "text": "Golgi apparatus",
          "correct": true,
          "justification": "The Golgi apparatus modifies, sorts, and packages proteins and lipids for transport within the cell."
        }
      ],
      "correct_option_ids": ["A", "B", "C", "E", "G"],
      "bloom_level": "remember",
      "task_difficulty": 1,
      "msq_difficulty": 3
    },
    {
      "question_type": "MSQ",
      "stem": "Which of the following are mechanisms of evolution? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Natural selection",
          "correct": true,
          "justification": "Natural selection favors individuals with advantageous traits, leading to changes in population genetics over generations."
        },
        {
          "id": "B",
          "text": "Genetic drift",
          "correct": true,
          "justification": "Genetic drift causes random changes in allele frequencies, particularly in small populations."
        },
        {
          "id": "C",
          "text": "Mutation",
          "correct": true,
          "justification": "Mutations create new genetic variations, providing raw material for evolutionary change."
        },
        {
          "id": "D",
          "text": "Acquired characteristics (Lamarckism)",
          "correct": false,
          "justification": "Lamarck's idea that organisms inherit traits acquired during their lifetime has been disproven and is not a valid mechanism of evolution."
        },
        {
          "id": "E",
          "text": "Gene flow (migration)",
          "correct": true,
          "justification": "Gene flow introduces new alleles into a population through the movement of individuals or gametes between populations."
        },
        {
          "id": "F",
          "text": "Reproductive isolation",
          "correct": false,
          "justification": "Reproductive isolation is a consequence of evolution that can lead to speciation, not a mechanism that causes genetic change within a population."
        },
        {
          "id": "G",
          "text": "Non-random mating",
          "correct": false,
          "justification": "Non-random mating changes genotype frequencies but does not directly change allele frequencies, so it is not considered a primary evolutionary mechanism."
        },
        {
          "id": "H",
          "text": "Artificial selection",
          "correct": false,
          "justification": "Artificial selection is driven by human intervention and is not a natural evolutionary mechanism, though it demonstrates similar principles."
        }
      ],
      "correct_option_ids": ["A", "B", "C", "E"],
      "bloom_level": "analyze",
      "task_difficulty": 3,
      "msq_difficulty": 2
    }
  ]
}
```
##### here's another example:
```JSON
{
  "subject": "World History",
  "grade_level": 9,
  "total_questions": 4,
  "generated_date": "2026-08-23",
  "questions": [
    {
      "question_type": "MSQ",
      "stem": "Which of the following were major causes of World War I? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Militarism",
          "correct": true,
          "justification": "Militarism involved the arms race and glorification of military power, which created tension and preparedness for war."
        },
        {
          "id": "B",
          "text": "Alliances",
          "correct": true,
          "justification": "The system of alliances (Triple Entente vs. Triple Alliance) created a web of obligations that drew nations into conflict."
        },
        {
          "id": "C",
          "text": "Imperialism",
          "correct": true,
          "justification": "Competition for colonies and resources created conflicts between European powers and heightened international tensions."
        },
        {
          "id": "D",
          "text": "Assassination of Archduke Franz Ferdinand",
          "correct": true,
          "justification": "The assassination was the immediate spark that triggered the war by activating the alliance system."
        },
        {
          "id": "E",
          "text": "Nationalism",
          "correct": true,
          "justification": "Nationalism fueled ethnic tensions, especially in the Balkans, and created a sense of superiority among nations."
        },
        {
          "id": "F",
          "text": "Treaty of Versailles",
          "correct": false,
          "justification": "The Treaty of Versailles was the peace settlement that ended WWI, not a cause of it."
        }
      ],
      "correct_option_ids": ["A", "B", "C", "D", "E"],
      "bloom_level": "understand",
      "task_difficulty": 2,
      "msq_difficulty": 3
    },
    {
      "question_type": "MSQ",
      "stem": "Which of the following were key figures of the American Revolution? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "George Washington",
          "correct": true,
          "justification": "Washington was the commander-in-chief of the Continental Army and later became the first U.S. President."
        },
        {
          "id": "B",
          "text": "Thomas Jefferson",
          "correct": true,
          "justification": "Jefferson was the primary author of the Declaration of Independence and a leading advocate for independence."
        },
        {
          "id": "C",
          "text": "Benjamin Franklin",
          "correct": true,
          "justification": "Franklin was a diplomat, scientist, and key figure in securing French support for the Revolution."
        },
        {
          "id": "D",
          "text": "King George III",
          "correct": false,
          "justification": "King George III was the British monarch against whom the colonists rebelled, not a figure of the Revolution."
        },
        {
          "id": "E",
          "text": "John Adams",
          "correct": true,
          "justification": "Adams was a leading advocate for independence and played a key role in the Continental Congress."
        },
        {
          "id": "F",
          "text": "Marquis de Lafayette",
          "correct": true,
          "justification": "Lafayette was a French nobleman who fought alongside the Americans and became a key ally."
        },
        {
          "id": "G",
          "text": "Napoleon Bonaparte",
          "correct": false,
          "justification": "Napoleon was a French military leader during the post-Revolution period, not involved in the American Revolution."
        },
        {
          "id": "H",
          "text": "Patrick Henry",
          "correct": true,
          "justification": "Henry was a fiery orator known for his 'Give me liberty or give me death!' speech, inspiring revolutionary sentiment."
        }
      ],
      "correct_option_ids": ["A", "B", "C", "E", "F", "H"],
      "bloom_level": "remember",
      "task_difficulty": 1,
      "msq_difficulty": 3
    },
    {
      "question_type": "MSQ",
      "stem": "Which of the following were significant inventions or innovations of the Industrial Revolution? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Steam engine",
          "correct": true,
          "justification": "The steam engine revolutionized transportation and manufacturing, enabling factories and railways."
        },
        {
          "id": "B",
          "text": "Cotton gin",
          "correct": true,
          "justification": "The cotton gin mechanized cotton processing, dramatically increasing production and the demand for slave labor."
        },
        {
          "id": "C",
          "text": "Telegraph",
          "correct": true,
          "justification": "The telegraph transformed communication by allowing instant long-distance messaging."
        },
        {
          "id": "D",
          "text": "Electric light bulb",
          "correct": false,
          "justification": "The electric light bulb was invented later (1879) and is associated with the Second Industrial Revolution."
        },
        {
          "id": "E",
          "text": "Spinning jenny",
          "correct": true,
          "justification": "The spinning jenny mechanized textile spinning, enabling faster and cheaper cloth production."
        },
        {
          "id": "F",
          "text": "Steel production process (Bessemer process)",
          "correct": false,
          "justification": "The Bessemer process for steelmaking came later (1850s) and is associated with the Second Industrial Revolution."
        },
        {
          "id": "G",
          "text": "Mechanical reaper",
          "correct": true,
          "justification": "The mechanical reaper revolutionized agriculture by allowing a single worker to harvest much more grain."
        }
      ],
      "correct_option_ids": ["A", "B", "C", "E", "G"],
      "bloom_level": "understand",
      "task_difficulty": 2,
      "msq_difficulty": 3
    },
    {
      "question_type": "MSQ",
      "stem": "Which of the following were key principles of the Enlightenment? Select all that apply.",
      "options": [
        {
          "id": "A",
          "text": "Reason and rationality",
          "correct": true,
          "justification": "Enlightenment thinkers championed reason as the primary source of knowledge and authority."
        },
        {
          "id": "B",
          "text": "Natural rights (life, liberty, property)",
          "correct": true,
          "justification": "Philosophers like John Locke argued that individuals possess inherent rights that governments must protect."
        },
        {
          "id": "C",
          "text": "Divine right of kings",
          "correct": false,
          "justification": "Enlightenment thinkers rejected the divine right of kings in favor of secular, rational governance."
        },
        {
          "id": "D",
          "text": "Separation of powers",
          "correct": true,
          "justification": "Montesquieu advocated for dividing government into branches to prevent tyranny."
        },
        {
          "id": "E",
          "text": "Social contract",
          "correct": true,
          "justification": "Thinkers like Rousseau argued that legitimate government derives from the consent of the governed."
        },
        {
          "id": "F",
          "text": "Freedom of religion",
          "correct": false,
          "justification": "While religious tolerance was a later development, it was not a primary focus of most Enlightenment philosophers."
        },
        {
          "id": "G",
          "text": "Scientific method and empiricism",
          "correct": true,
          "justification": "Enlightenment thinkers promoted empiricism and the scientific method as ways to understand the natural world."
        }
      ],
      "correct_option_ids": ["A", "B", "D", "E", "G"],
      "bloom_level": "analyze",
      "task_difficulty": 3,
      "msq_difficulty": 3
    }
  ]
}
```

### VERY IMPROTANT TO FOLLOW:
your output is a SINGLE json block, containing all the questions. 
""".strip()


MSQ_BLOOM_LEVELS="""
# 12. Bloom levels most suitable for MSQs

MSQ format is not equally suitable for every Bloom level.

The strongest fit is generally are the bloom levels:
- Remember
- Understand

moderate fit for:
- Apply
- Analyze

Don't use for:
- Evaluate
- Create

---

# Remember + MSQ

## Suitability: Very High

MSQs work naturally for Remember when several facts must be recognized.

Example:

> **Which of the following are HTTP request methods? Select all that apply.**
> 
> [x] GET  
> [x] POST  
> [ ] SQL  
> [x] DELETE  
> [ ] HTML

This tests recognition/retrieval.

### Best MSQ difficulties
MSQ level 1: Excellent
MSQ level 2: Suitable
MSQ level 3: Suitable when precise factual discrimination is intended
```

Example of Remember + MSQ level 3:

> Which of the following HTTP status codes indicate client errors? Select all that apply.

The learner must discriminate among closely related status-code categories.

---

# Understand + MSQ

## Suitability: Very High

MSQs are particularly useful for understanding because each option can represent:

- a correct interpretation,
    
- a misconception,
    
- an incorrect relationship,
    
- an incomplete explanation.
    

Example:

> **Which statements correctly describe inheritance in object-oriented programming? Select all that apply.**

This can test whether the learner understands conceptual relationships rather than merely remembering terminology.

### Best MSQ difficulties
- MSQ level 1: Good
- MSQ level 2: Excellent
- MSQ level 3: Excellent

This is probably one of the strongest uses of MSQ.

---

# Apply + MSQ

## Suitability: High

An MSQ can present multiple cases and ask the learner to select those where a rule, method, or principle correctly applies.

Example:

> **Given the following code snippets, which will raise an exception when executed? Select all that apply.**

The learner must apply knowledge to each option.

Another example:

> **Which equations can be solved using the quadratic formula? Select all that apply.**

### Best MSQ difficulties

```text
MSQ level 1: Suitable
MSQ level 2: Excellent
MSQ level 3: Excellent
```

For Apply, MSQ 3 can use cases with:
- exceptions,
- boundary conditions,
- superficially similar inputs requiring different procedures.
    

---

# Analyze + MSQ

## Suitability: Moderate to High

MSQs can work for Analyze when each option requires the learner to identify:
- components,
- relationships,
- causes,
- structural properties,
- patterns,
- errors.
    
Example:

> **Based on the execution trace, which factors contribute to the observed performance bottleneck? Select all that apply.**

Each option represents a possible causal factor.

However, the stem must provide enough information to actually perform analysis.

Bad:

> Which of the following are causes of poor performance?

That may just test Remember.

Better:

> Given the profiling data below, which factors are contributing to the bottleneck?

Now the learner must analyze evidence.

### Best MSQ difficulties
MSQ level 1: Limited
MSQ level 2: Good
MSQ level 3: Very useful


The highest-quality Analyze MSQs usually require meaningful case interpretation.
""".strip()
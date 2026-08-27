Implement "2. Option-level consistency
This is particularly important for your MSQ validator.
Your validation output intentionally does not contain the full original question, but `option_validations` contains:

```
```

```
{
  "option": {
    "id": "A",
    "text": "..."
  },
  "original_correct": true,
  ...
}
```

Therefore compare those against the original question.
For every original option:

```
```

```
original.options[i]
```

there must be exactly one:

```
```

```
validation.answer_correctness.option_validations[i]
```

### 2.1 Same number of options

```
```

```
len(original.options)
==
len(validation.option_validations)
```

### 2.2 Same option order

Since your schema explicitly says:

> There must be exactly one object for every input option, in the same order as the input options.

verify:

```
```

```
A → A
B → B
C → C
...
```

not merely that the set is equal.

### 2.3 Option ID equality

For every position:

```
```

```
validation.option_validations[i].option.id
==
original.options[i].id
```

### 2.4 Option text equality

Likewise:

```
```

```
validation.option_validations[i].option.text
==
original.options[i].text
```

You said slight stem differences are acceptable, but for option text I would be much stricter. The validator is supposed to identify the exact option being evaluated.
You can allow whitespace normalization, but I would not use aggressive fuzzy matching here.

### 2.5 `original_correct` must exactly copy the source

This is a direct consistency rule:

```
```

```
validation.option_validations[i].original_correct
==
original.options[i].correct
```

The LLM is **not allowed to reinterpret this field**.
This field means:

> "What did the original generated question say?"

It does not mean:

> "What do I think the answer should be?

"
where if there is any fixable inconsistency, the code fixes it.
For example, the id ordering or if there's a difference in ids of the options in the validation schema doesn't match the ones in the questions schema, the code fixes it.
Only if the text is different or an option is missing (slight differences are ignorable. if options have close similarity it's fine (for example a missing "is" or "are vs"is" ..such minor things won't affect similarity or meaning much. ) then it removes the this item from the validation schema into the file in the `invalid` folder and removes the question from the questions schema and adds it to the file in the orphan folder.
for questions schema We will use path: F:\pythonProj\question\_generator\final\_schemas\questions\valid for our input folder and also as the path where file that we will update. (remove the bad ones)
same for validation schema: F:\pythonProj\question\_generator\final\_schemas\validations\valid
And make sure you ADD the invalid ones to the invalid files without overwriting the old ones.
So, the invalid questions schema goes into path: F:\pythonProj\question\_generator\final\_schemas\questions\orphan
and the invalid validations schema goes into path: F:\pythonProj\question\_generator\final\_schemas\validations\invalid
with the same naming convention `node_id` parameter which is the name of input files.

While updating this file: 
F:\pythonProj\question\_generator\final\_schemas\validations\isometries\_metadata.json
which already contains this data:
{
  "node\_id": "isometries",
  "input\_files": {
    "questions": "F:\\\pythonProj\\\question\_generator\\\llm\_response\_generations\\\jsons\_with\_ids\\\isometries.txt",
    "validation": "F:\\\pythonProj\\\question\_generator\\\llm\_validation\\\cleaned\_json\\\isometries.txt"
  },
  "matching": {
    "stem\_similarity\_threshold": 0.92,
    "matched\_by\_id": 23,
    "matched\_by\_stem": 0,
    "invalid\_validation\_questions": 0,
    "id\_matched\_but\_stem\_mismatch": 0,
    "average\_stem\_similarity": 1.0
  },
  "counts": {
    "input\_questions": 23,
    "input\_validation\_questions": 23,
    "valid\_validation\_questions": 23,
    "valid\_questions": 23,
    "orphan\_questions": 0
  },
  "outputs": {
    "valid\_validation": "F:\\\pythonProj\\\question\_generator\\\final\_schemas\\\validations\\\valid\\\isometries.json",
    "invalid\_validation": null,
    "valid\_questions": "F:\\\pythonProj\\\question\_generator\\\final\_schemas\\\questions\\\valid\\\isometries.json",
    "orphan\_questions": null
  }
}
So we update the counting here. 




Yes. The metadata should be attached to the question object in questions/valid, and it should behave monotonically:

modified == True is permanent.
Existing modified == True is never changed back to False.
Existing modified == False becomes True when this reconciliation pass detects and repairs an inconsistency.
Existing reason:
null → replaced with the new reason when modified.
non-empty string → new reason is appended.
existing content is never overwritten.
when no modification occurs, it is left untouched.
If modified does not exist:
True when this pass makes an adjustment.
False otherwise.
If reason does not exist:
new reason when modified.
null when not modified.

One important point: your current function repairs the validation JSON, not the original question's answer values. Therefore, the metadata should describe the inconsistency/reconciliation that was detected, not claim that the original question itself was altered.

Also, because your questions schema previously had "additionalProperties": false, adding modified and reason means that schema should be updated to allow these two fields.
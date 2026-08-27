now, write code that does the following:

# 3. Answer-set consistency

You have three separate representations of the answer:

### Original question


```
options[].correct
```

and:


```
correct_option_ids
```

### Validation output


```
provided_correct_option_ids
```

and:


```
verified_correct_option_ids
```

and:


```
option_validations[].independently_verified_correct
```

These should form a consistency chain.

---

## 3.1 `provided_correct_option_ids` must exactly match the source

Compute:


```
source_correct_ids = {
    option["id"]
    for option in original["options"]
    if option["correct"] is True
}
```

Then verify:


```
set(validation.provided_correct_option_ids)
==
set(original.correct_option_ids)
```

Because your schema says this field is:

> the exact `correct_option_ids` supplied in the input question, copied without modification.

Therefore I would actually consider **ordering** too:


```
validation.provided_correct_option_ids
==
original.correct_option_ids
```

not merely set equality.

That preserves the "copied exactly" semantics.

If there are any inconsistencies, fix the values and make them consistent. so, this code doesn't invalidate at all, it just fixes if there's any inconsistency and returns the adjust JSON (Adjustment only happens in the validation schema) UPDATING the same file. So input files are 
questions schema: F:\pythonProj\question\_generator\final\_schemas\questions\valid 
 same for validation schema: F:\pythonProj\question\_generator\final\_schemas\validations\valid  
and output file is also schema: F:\pythonProj\question\_generator\final\_schemas\validations\valid where updated schema is returned. (overriding old schema) 
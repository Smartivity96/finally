---
name: openai-inference
description: Use this to write code to call an LLM using LiteLLM and the OpenAI API
---

# Calling an LLM via OpenAI

These instructions allow you to write code to call an OpenAI model through LiteLLM.

## Setup

The OPENAI_API_KEY must be set in the .env file and loaded in as an environment variable.  

The uv project must include litellm and pydantic.
`uv add litellm pydantic`

## Code snippets

Use code like these examples in order to call OpenAI.

### Imports and constants

```python
from litellm import completion
MODEL = "openai/gpt-5-mini"
```

### Code to call OpenAI for a text response

```python
response = completion(model=MODEL, messages=messages, reasoning_effort="low")
result = response.choices[0].message.content
```

### Code to call OpenAI for a Structured Outputs response

```python
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass, reasoning_effort="low")
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```

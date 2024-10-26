"""
Basic call to Gemini.

GWGS is Grounding with Google Search. GWGS is off by defualt
because it is expensive.
Safety is off by default.
"""

import vertexai, os
from vertexai.preview.generative_models import GenerativeModel, Part, SafetySetting, Tool
from vertexai.preview.generative_models import grounding

PROJECT_ID = os.getenv("PROJECT_ID")

vertexai.init(project=PROJECT_ID, location="us-central1")

def generate(prompt, temp = 0.1, safety_off = True, gwgs = False, json_on = False):
  generation_config = {
    "max_output_tokens": 8192,
    "temperature": temp,
    "response_mime_type": "application/json" if json_on else "text/plain",
    # NOTE: add 'responseSchema' to define json response format
  }

  if safety_off:
    safety_settings = [
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
    ]
  else:
     safety_settings = [
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        ),
     ]

  if gwgs:
    tools = [
        Tool.from_google_search_retrieval(
            google_search_retrieval=grounding.GoogleSearchRetrieval()
        ),
    ]
  else:
    tools = []

  model = GenerativeModel(
      "gemini-1.5-flash-002",
      tools=tools,
  )
  response = model.generate_content(
      prompt,
      generation_config=generation_config,
      safety_settings=safety_settings,
      stream=False,

  )

  return response

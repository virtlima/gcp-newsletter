"""
Basic call to Gemini.

GWGS is Grounding with Google Search. GWGS is off by defualt
because it is expensive.
Safety is off by default.
"""

import os
from google import genai
from google.genai import types

PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

genai_client = genai.Client(
    vertexai=True, project=PROJECT_ID, location='us-central1'
)

def generate(prompt, temp = 0.1, json_on = False):
  response = genai_client.models.generate_content(
      model='gemini-2.5-flash',
      contents=prompt,
      config=types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=temp,
        response_mime_type="application/json" if json_on else "text/plain",
      )
  )

  return response

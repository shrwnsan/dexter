import os
import time
import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Type, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage
from openai import APIConnectionError

from dexter.prompts import DEFAULT_SYSTEM_PROMPT
from dexter.utils.api_security import get_openai_api_key, validate_all_required_keys
from dexter.utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

# Initialize the OpenAI client with secure API key management
# API keys are validated for security before use
@rate_limit(api_type="openai", cost=0.02)  # OpenAI API calls cost more
def call_llm(
    prompt: str,
    model: str = "gpt-4.1",
    system_prompt: Optional[str] = None,
    output_schema: Optional[Type[BaseModel]] = None,
    tools: Optional[List[BaseTool]] = None,
) -> AIMessage:
  final_system_prompt = system_prompt if system_prompt else DEFAULT_SYSTEM_PROMPT

  prompt_template = ChatPromptTemplate.from_messages([
      ("system", final_system_prompt),
      ("user", "{prompt}")
  ])

  # Initialize the LLM with validated API key
  try:
      validated_api_key = get_openai_api_key()
      llm = ChatOpenAI(model=model, temperature=0, api_key=validated_api_key)
  except Exception as e:
      logger.error(f"Failed to initialize OpenAI client: {e}")
      raise

  # Add structured output or tools to the LLM.
  runnable = llm
  if output_schema:
      runnable = llm.with_structured_output(output_schema, method="function_calling")
  elif tools:
      runnable = llm.bind_tools(tools)
  
  chain = prompt_template | runnable
  
  # Retry logic for transient connection errors
  for attempt in range(3):
      try:
          return chain.invoke({"prompt": prompt})
      except APIConnectionError as e:
          if attempt == 2:  # Last attempt
              raise
          time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s backoff

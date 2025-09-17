from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
from openai import OpenAI
import json
import os
import re
import logging
from extractor import robust_extract_text
# import google.generativeai as genai  # Uncomment if using Google Generative AI
# Configure logging
# Save logs to a file and set the logging level ./logs/app.log
# Create a logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='./logs/app.log')

# Initialize FastAPI app

app = FastAPI()
print("Starting FastAPI app...")

# Load environment variables
from dotenv import load_dotenv
load_dotenv("./.env")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisResult(BaseModel):
    summary: str
    score: int


def fix_a_json_string(json_string: str) -> str:
    """
    Attempts to fix a malformed JSON string by:
    - Replacing single quotes with double quotes
    - Removing trailing commas before closing brackets
    - Using regex for further cleanup if needed
    - As a last resort, using an AI model to attempt a fix
    Returns a JSON string that is as valid as possible.
    """
    def is_valid_json(s: str) -> bool:
        try:
            json.loads(s)
            return True
        except json.JSONDecodeError:
            return False
    
    # step 0: Check if the string is already valid JSON
    if is_valid_json(json_string):
        logging.info("JSON string is already valid.")
        return json_string
    logging.warning("JSON string is not valid, attempting to fix...")
    # Step 1: Remove code block markers if present
    # remove ```json
    json_string = re.sub(r'```json\s*', '', json_string)
    # remove ``` at the end
    json_string = re.sub(r'```$', '', json_string)
    if is_valid_json(json_string):
        logging.info("JSON string is valid after removing code block markers.")
        return json_string
    # Step 2: Replace single quotes with double quotes
    fixed = json_string.replace("'", '"') 
    if is_valid_json(fixed):
        logging.info("Fixed JSON string is valid after replacing single quotes and removing trailing commas.")
        return fixed

    # Step 3: As a last resort, use AI to fix the JSON string
    logging.warning("Still invalid JSON format after regex fix. Attempting AI-based fix.")
    fixed = analyze_with_fix_streaming(
        json_string,
        system_prompt="""You are an expert in fixing JSON strings. Do not provide any comment, just a plain json string. Please identifiy any potential errors and provide solutions for these errors. Example is you will do the following when you encounter quotes within the string values:
        1. Use \\" to escape quotes within JSON string values
        2. Building the object directly in Python avoids string escaping issues entirely
        Check the following JSON string for errors and fix it
        """,
        model_name="claude-3-7-sonnet-20250219",
        run_fix=False  # Set to False to avoid recursive calls
    )
    if is_valid_json(fixed):
        logging.info("AI successfully fixed the issue and it is a valid JSON.")
        return fixed
    else:
        logging.error("AI-based fix also failed to produce valid JSON.")
        # If AI fix fails, return the original string or an error message
        return fixed


def analyze_with_fix_streaming(text, system_prompt, model_name, run_fix=True):
        """
        Analyze text using Claude with streaming to avoid timeout issues.
        """
        client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])

        # Use streaming by default for Claude
        # Count the number of words in the input text and system prompt
        word_count = len((text + " " + system_prompt).split())
        # Use a safe multiplier to estimate max_tokens (assuming ~1.3 tokens per word)
        max_tokens = int(round(4.0 * word_count))
        logging.info(f"Estimated max_tokens for Claude: {max_tokens} (based on word count: {word_count})")
        if max_tokens > 4096:
            with client.messages.stream(
                model=model_name,
                max_tokens=max_tokens,  # Use word-based estimation
                temperature=0.01,
                system=system_prompt,
                messages=[{"role": "user", "content": text}]
            ) as stream:
                response_text = ""
                for text_chunk in stream.text_stream:
                    response_text += text_chunk
            logging.info(f"Claude streaming response: {response_text.strip()}")
            if run_fix:
                output = fix_a_json_string(response_text.strip())
            else:
                output = response_text.strip()
            return output
        else:
            message = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,  # Lower limit for fallback
                temperature=0.01,
                system=system_prompt,
                messages=[{"role": "user", "content": text}]
            )
            if run_fix:
                logging.info(f"Claude response: {message.content[0].text.strip()}")
                output = fix_a_json_string(message.content[0].text.strip())
            else:
                logging.info(f"Claude response: {message.content[0].text.strip()}")
                output = message.content[0].text.strip()
            return output


def analyze_with_claude_streaming(text, system_prompt, model_name, run_fix=True):
        """
        Analyze text using Claude with streaming to avoid timeout issues.
        """
        client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])

        # Use streaming by default for Claude
        # Count the number of words in the input text and system prompt
        word_count = len((text + " " + system_prompt).split())
        # Use a safe multiplier to estimate max_tokens (assuming ~1.3 tokens per word)
        max_tokens = int(round(1.3 * word_count))
        logging.info(f"Estimated max_tokens for Claude: {max_tokens} (based on word count: {word_count})")
        if max_tokens > 4096:
            with client.messages.stream(
                model=model_name,
                max_tokens=max_tokens,  # Use word-based estimation
                temperature=0.01,
                system=system_prompt,
                messages=[{"role": "user", "content": text}]
            ) as stream:
                response_text = ""
                for text_chunk in stream.text_stream:
                    response_text += text_chunk
            logging.info(f"Claude streaming response: {response_text.strip()}")
            if run_fix:
                output = fix_a_json_string(response_text.strip())
            else:
                output = response_text.strip()
            return output
        else:
            message = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,  # Lower limit for fallback
                temperature=0.01,
                system=system_prompt,
                messages=[{"role": "user", "content": text}]
            )
            if run_fix:
                logging.info(f"Claude response: {message.content[0].text.strip()}")
                output = fix_a_json_string(message.content[0].text.strip())
            else:
                logging.info(f"Claude response: {message.content[0].text.strip()}")
                output = message.content[0].text.strip()
            return output

def analyze_with_deepseek_streaming(text, system_prompt, model_name, ):
        """
        Analyze text using DeepSeek with streaming to avoid timeout issues.
        """
        client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

        # Use streaming by default for DeepSeek
        # Count the number of words in the input text and system prompt
        word_count = len((text + " " + system_prompt).split())
        # Use a safe multiplier to estimate max_tokens (assuming ~1.3 tokens per word)
        max_tokens = int(round(1.3 * word_count))
        logging.info(f"Estimated max_tokens for DeepSeek: {max_tokens} (based on word count: {word_count})")
        if max_tokens > 4096:
            with client.chat.completions.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=0.01,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                stream=True
            ) as stream:
                response_text = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        text_chunk = chunk.choices[0].delta.content
                        response_text += text_chunk
            logging.info(f"DeepSeek streaming response: {response_text.strip()}")
            output = fix_a_json_string(response_text.strip())
            return output
        else:
            message = client.chat.completions.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=0.01,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                stream=False
            )
            content = message.choices[0].message.content.strip()
            logging.info(f"DeepSeek streaming response: {content}")
            output = fix_a_json_string(content)
            return output


def analyze_with_openai(text, system_prompt="You are an expert reviewer for onboarding literature for physician.", model_name="gpt-4-1106-preview"):
    """
    Analyze text using OpenAI's GPT model.
    """
    client = OpenAI(api_key=os.environ["OpenAI_API_KEY"])
    
    # Count the number of words in the input text and system prompt
    word_count = len((text + " " + system_prompt).split())
    # Use a safe multiplier to estimate max_tokens (assuming ~1.3 tokens per word)
    max_tokens = int(round(1.3 * word_count))
    logging.info(f"Estimated max_tokens for OpenAI: {max_tokens} (based on word count: {word_count})")
    if max_tokens > 4096:
        # Use streaming for larger inputs
        with client.chat.completions.create(
            model=model_name,
            max_completion_tokens=max_tokens,  # Use word-based estimation
            # temperature=0.01,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            stream=True
        ) as stream:
            response_text = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    response_text += text_chunk
        logging.info(f"OpenAI streaming response: {response_text.strip()}")
        return fix_a_json_string(response_text.strip())
    else:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            max_completion_tokens=max_tokens
            # temperature=0.01
        )
        
        content = response.choices[0].message.content
        logging.info(f"OpenAI streaming response: {content.strip()}")
        return fix_a_json_string(content.strip() if content else "")

def analyze_with(text, system_prompt="You are an expert reviewer for onboarding literature for physician.", model_name="claude-3-7-sonnet-20250219"):
    """
    Main analysis function that routes to appropriate AI service.
    """
    try:
        if 'claude' in model_name.lower():
            return analyze_with_claude_streaming(text, system_prompt, model_name)
        elif 'deepseek' in model_name.lower():                
            return analyze_with_deepseek_streaming(text, system_prompt, model_name)
        else:
            return analyze_with_openai(text, system_prompt, model_name)
    
    except Exception as e:
        logging.error(f"Error in analyze_with: {e}")
        return json.dumps({"summary": f"Error: {str(e)}", "score": 0})


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_pdf(
    file: UploadFile = File(...),
    system_prompt: str = Form(None),
    user_prompt: str = Form(None),
    model: str = Form("claude-3-7-sonnet-20250219")
):
    logging.info("Received request to analyze PDF")
    logging.info(f"Received file: {file.filename}")
    logging.info(f"System prompt: {system_prompt}")
    logging.info(f"User prompt: {user_prompt}")
    logging.info(f"Model: {model}")
    logging.info(f"File size: {file.file.seek(0, 2)} bytes")  # Log file size
    
    try:
        # Extract text from PDF
        text = robust_extract_text(file)
        
        if user_prompt:
            # Append user prompt to the text for analysis
            text = f"User prompt: {user_prompt} \n\n {text}"
        
        if len(text) < 500:
            return {"summary": "Text too short or not extractable.", "score": 0}
        
        # Analyze with selected model
        summary = analyze_with(text, system_prompt=system_prompt, model_name=model)
        
        # Calculate simple score based on keywords
        score = sum(keyword in text.lower() for keyword in ["onboarding", "specific", "flow", "generalist"])
        
        return {"summary": summary, "score": min(score, 5)}
    
    except Exception as e:
        logging.error(f"Error in analyze_pdf: {e}")
        return {"summary": f"Error processing file: {str(e)}", "score": 0}

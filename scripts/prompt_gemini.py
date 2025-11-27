import os
import json
import sys
import google.generativeai as genai
import time

def get_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def generate_with_fallback(prompt):
    """Attempts generation with Flash, falls back to Pro if not found."""
    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }

    models_to_try = ['gemini-1.5-flash', 'gemini-pro']
    
    for model_name in models_to_try:
        try:
            print(f"Attempting to use model: {model_name}...")
            model = genai.GenerativeModel(model_name, generation_config=generation_config)
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            print(f"Failed with {model_name}: {str(e)}")
            # If it's a quota error (429), we should wait and retry the SAME model, not switch.
            # But if it's 404 (Not Found), we switch to the next model.
            if "404" in str(e) or "not found" in str(e).lower():
                continue # Try next model
            else:
                raise e # Re-raise other errors (like Auth or Quota) to be handled by main loop
    
    raise Exception("All models failed.")

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    diff_content = get_file_content("dff.txt") or "No changes detected."
    
    # Strict truncation for 1.5 Flash (approx 100k tokens safe limit)
    # For gemini-pro fallback (32k tokens), we might need even stricter truncation.
    MAX_CHARS = 100000 
    if len(diff_content) > MAX_CHARS:
        print(f"Truncating diff from {len(diff_content)} to {MAX_CHARS} chars.")
        diff_content = diff_content[:MAX_CHARS] + "\n...[TRUNCATED]..."

    test_cases_content = get_file_content("test_case.txt")
    if not test_cases_content:
        print("Error: test_case.txt is missing.")
        sys.exit(1)

    prompt = f"""
    You are a Software Engineering Assistant.
    Task: Analyze Code Changes and assess Test Case relevance.
    
    CONTEXT:
    --- GIT DIFF ---
    {diff_content}
    --- END DIFF ---
    
    --- TEST CASES ---
    {test_cases_content}
    --- END TEST CASES ---
    
    OUTPUT INSTRUCTIONS:
    Return a JSON object where keys are Test Case IDs.
    Values must be objects with: "relevance" (0.0-1.0), "complexity" (0.0-1.0), "change_nature" (string).
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = generate_with_fallback(prompt)
            
            # Clean response text just in case markdown is included despite MIME type
            text = response.text.replace('```json', '').replace('```', '').strip()
            json_data = json.loads(text)
            
            with open("llm.txt", "w", encoding='utf-8') as f:
                json.dump(json_data, f, indent=4)
                
            print(f"Success! Generated llm.txt with {len(json_data)} entries.")
            sys.exit(0)

        except Exception as e:
            print(f"Error on attempt {attempt+1}: {str(e)}")
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(30)
            else:
                if attempt == max_retries - 1:
                    sys.exit(1)

if __name__ == "__main__":
    main()
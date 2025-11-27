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

def find_available_model():
    """
    Dynamically queries the API to find a usable model.
    Prioritizes 'flash' models for speed, then 'pro'.
    """
    print("🔍 Discovery: querying available Gemini models...")
    try:
        available_models = []
        # iterate over all models available to this API key
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"✅ Found models: {available_models}")
        
        # Strategy 1: Look for 1.5 Flash (Best for this task)
        for m in available_models:
            if 'gemini-1.5-flash' in m:
                return m
                
        # Strategy 2: Look for any Flash model
        for m in available_models:
            if 'flash' in m.lower():
                return m
        
        # Strategy 3: Look for Pro model (Fallback)
        for m in available_models:
            if 'gemini-pro' in m or 'gemini-1.5-pro' in m:
                return m
                
        # Strategy 4: Take the first available Gemini model
        if available_models:
            return available_models[0]
            
    except Exception as e:
        print(f"⚠️ Error listing models: {e}")
        
    # Absolute fallback if discovery fails completely
    return 'gemini-1.5-flash'

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    # 1. Select Model Dynamically
    model_name = find_available_model()
    print(f"🚀 Selected Model: {model_name}")

    # 2. Load Data
    diff_content = get_file_content("dff.txt") or "No changes detected."
    
    # Dynamic truncation based on model capability
    # Flash models can handle ~1M tokens, Pro models ~32k
    if 'flash' in model_name.lower():
        MAX_CHARS = 300000 # ~75k tokens (Safe for Free Tier Flash)
    else:
        MAX_CHARS = 80000  # ~20k tokens (Safe for Pro)
        
    if len(diff_content) > MAX_CHARS:
        print(f"Truncating diff from {len(diff_content)} to {MAX_CHARS} chars for {model_name}.")
        diff_content = diff_content[:MAX_CHARS] + "\n...[TRUNCATED]..."

    test_cases_content = get_file_content("test_case.txt")
    if not test_cases_content:
        print("Error: test_case.txt is missing.")
        sys.exit(1)

    # 3. Prepare Prompt
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

    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }

    # 4. Execute with Retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Sending request (Attempt {attempt+1})...")
            model = genai.GenerativeModel(model_name, generation_config=generation_config)
            response = model.generate_content(prompt)
            
            # Parse Response
            text = response.text.replace('```json', '').replace('```', '').strip()
            json_data = json.loads(text)
            
            # Save output
            with open("llm.txt", "w", encoding='utf-8') as f:
                json.dump(json_data, f, indent=4)
                
            print(f"Success! Generated llm.txt with {len(json_data)} entries.")
            sys.exit(0)

        except Exception as e:
            print(f"Error on attempt {attempt+1}: {str(e)}")
            if "429" in str(e) and attempt < max_retries - 1:
                print("Quota limit hit. Waiting 30s...")
                time.sleep(30)
            else:
                if attempt == max_retries - 1:
                    print("❌ All attempts failed.")
                    sys.exit(1)

if __name__ == "__main__":
    main()
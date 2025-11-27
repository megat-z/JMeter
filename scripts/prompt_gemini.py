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

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    diff_content = get_file_content("dff.txt")
    if not diff_content:
        print("Warning: dff.txt is empty or missing. Assuming no code changes.")
        diff_content = "No changes detected."
    MAX_CHARS = 300000
    if len(diff_content) > MAX_CHARS:
        print(f"Warning: Diff is extremely large ({len(diff_content)} chars). Truncating to {MAX_CHARS}...")
        diff_content = diff_content[:MAX_CHARS] + "\n...[TRUNCATED]..."

    test_cases_content = get_file_content("test_case.txt")
    if not test_cases_content:
        print("Error: test_case.txt is missing or empty in the root directory.")
        sys.exit(1)

    prompt = f"""
    You are a specialized Software Engineering Assistant for Test Case Prioritization.
    Task: Analyze the following Code Changes (Git Diff) and assess the relevance of the provided Test Cases.
    CONTEXT:
    --- BEGIN GIT DIFF ---
    {diff_content}
    --- END GIT DIFF ---
    --- BEGIN TEST CASES ---
    {test_cases_content}
    --- END TEST CASES ---
    INSTRUCTIONS:
    1. Analyze the semantic intent of the code changes.
    2. For EACH test case listed in the context, return a JSON object with:
       - "relevance": float 0.0 to 1.0.
       - "complexity": float 0.0 to 1.0.
       - "change_nature": string (e.g., "logic_change", "refactor", "none").
    """
    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)
            
            print(f"Sending request to Gemini (Attempt {attempt+1})...")
            response = model.generate_content(prompt)
            
            # 5. Parse and Save
            json_data = json.loads(response.text)
            
            if not json_data:
                print("Warning: Gemini returned empty JSON.")

            with open("llm.txt", "w", encoding='utf-8') as f:
                json.dump(json_data, f, indent=4)
                
            print(f"Successfully generated llm.txt with {len(json_data)} entries.")
            sys.exit(0) # Success

        except Exception as e:
            print(f"Error communicating with Gemini: {str(e)}")
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = 30
                print(f"Quota exceeded. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                sys.exit(1)

if __name__ == "__main__":
    main()
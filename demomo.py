
import google.generativeai as genai
genai.configure(api_key="AQ.Ab8RN6L4bZLHqYoG2_B2iB80OvfcMSv9FVjqmkJbYTfAKqA8KQ")
for m in genai.list_models():
    print(m.name)
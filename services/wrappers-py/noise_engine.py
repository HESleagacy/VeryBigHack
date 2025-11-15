import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

paraphrase_model = None
paraphrase_tokenizer = None
T5_MODEL_NAME = "humarin/chatgpt_paraphraser_on_T5_base"

def load_paraphraser_model():
    """
    Loads the T5 paraphraser model and tokenizer into global variables.
    This is called once at startup by main.py.
    """
    global paraphrase_model, paraphrase_tokenizer
    
    if paraphrase_model is None:
        print(f"Loading T5 model: {T5_MODEL_NAME}...")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        paraphrase_tokenizer = AutoTokenizer.from_pretrained(T5_MODEL_NAME)
        paraphrase_model = AutoModelForSeq2SeqLM.from_pretrained(T5_MODEL_NAME).to(device)
        print("T5 model loading complete.")

async def _get_clean_answer_from_deepseek(prompt: str, api_key: str) -> str:
    """
    Helper function to get the "clean" (original) answer from DeepSeek.
    """
    try:
        print("... Calling DeepSeek (Primary LLM)")
        
        chat = ChatOpenAI(
            temperature=0.7, 
            api_key=api_key, 
            base_url="https://api.deepseek.com/v1",
            model_name="deepseek-chat"
        )
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Answer the user's question clearly and concisely."),
            ("human", "{user_prompt}")
        ])
        
        chain = prompt_template | chat | StrOutputParser()
        
        clean_answer = await chain.ainvoke({"user_prompt": prompt})
        return clean_answer

    except Exception as e:
        print(f"ERROR in DeepSeek call: {e}")
        return "[ERROR: Failed to get response from DeepSeek]"

def _get_noisy_answer_from_hf(clean_answer: str) -> str:
    """
    Helper function to get the "noisy" (paraphrased) answer
    from the pre-loaded T5 model.
    """
    global paraphrase_model, paraphrase_tokenizer
    
    if not paraphrase_model or not paraphrase_tokenizer:
        print("ERROR: T5 model not loaded. Returning clean answer as fallback.")
        return clean_answer
    
    try:
        print(f"... Calling T5 (Noise LLM)")

        input_text = f"paraphrase: {clean_answer}"
        
        device = paraphrase_model.device

        inputs = paraphrase_tokenizer(
            input_text, 
            return_tensors="pt", 
            max_length=512, 
            truncation=True
        ).to(device)

        noisy_outputs = paraphrase_model.generate(
            **inputs,
            max_length=512,
            num_beams=5,
            early_stopping=True
        )

        noisy_answer = paraphrase_tokenizer.decode(
            noisy_outputs[0], 
            skip_special_tokens=True
        )
        
        if noisy_answer.startswith("paraphrase: "):
             noisy_answer = noisy_answer[len("paraphrase: "):].strip()
        
        return noisy_answer

    except Exception as e:
        print(f"ERROR in T5 paraphrasing: {e}")
        return clean_answer

async def generate_noisy_response(prompt: str, deepseek_api_key: str) -> dict:
    """
    Orchestrates the full "poisoning" chain.
    
    1. Gets clean answer from DeepSeek.
    2. Paraphrases it with T5.
    3. Returns both.
    """
    clean_answer = await _get_clean_answer_from_deepseek(prompt, deepseek_api_key)
    noisy_answer = _get_noisy_answer_from_hf(clean_answer)
    
    return {
        "clean_answer": clean_answer,
        "noisy_answer": noisy_answer
    }

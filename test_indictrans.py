import os
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

if os.name == 'nt':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    torch_lib = os.path.join(base_dir, "venv", "Lib", "site-packages", "torch", "lib")
    if os.path.exists(torch_lib):
        import ctypes
        try: os.add_dll_directory(torch_lib)
        except: pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def test_translation():
    model_id = "ai4bharat/indictrans2-en-indic-dist-200m"
    print(f"DEBUG: Loading {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id, trust_remote_code=True)
    
    device = "cpu"
    model = model.to(device)
    
    text = "A beautiful sunset over the mountains."
    tgt_lang = "hin_Deva"
    src_lang = "eng_Latn"
    
    print(f"DEBUG: Special Tokens: {tokenizer.all_special_tokens[:10]}...")
    
    # Official IndicTrans2 logic often requires the IndicProcessor, but we use raw:
    # 1. Set identifiers
    tokenizer.src_lang = src_lang
    tokenizer.tgt_lang = tgt_lang
    
    # 2. Extract Lang ID from the tokenizer
    # IndicTrans2 uses the last token as the target language indicator sometimes
    # or expects it as forced_decoder_ids[0].
    
    print(f"DEBUG: Translating '{text}' to {tgt_lang}...")
    
    try:
        inputs = tokenizer(text, return_tensors="pt").to(device)
        
        # Check for lang_code_to_id
        if hasattr(tokenizer, 'lang_code_to_id'):
            print(f"DEBUG: Using lang_code_to_id. hin_Deva ID: {tokenizer.lang_code_to_id.get(tgt_lang)}")
            forced_id = tokenizer.lang_code_to_id.get(tgt_lang)
        else:
            print("DEBUG: No lang_code_to_id. Searching in vocab...")
            forced_id = tokenizer.convert_tokens_to_ids(tgt_lang)
            print(f"DEBUG: hin_Deva ID from vocab: {forced_id}")

        with torch.no_grad():
            generated_tokens = model.generate(
                **inputs,
                forced_decoder_ids=[(1, forced_id)] if forced_id is not None else None,
                max_length=256
            )
            
        result = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        print(f"RESULT (With forced_id): {result}")
        
        # Try second method: Prepend tag (Some IndicTrans2 versions need this)
        text_with_tag = f"{src_lang} {text}"
        inputs_tag = tokenizer(text_with_tag, return_tensors="pt").to(device)
        with torch.no_grad():
            gen_tag = model.generate(**inputs_tag, forced_decoder_ids=[(1, forced_id)] if forced_id is not None else None)
        res_tag = tokenizer.batch_decode(gen_tag, skip_special_tokens=True)[0]
        print(f"RESULT (With tag prefix): {res_tag}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_translation()

import os
import torch
from transformers import AutoTokenizer

model_id = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(model_id)

print(f"DEBUG: Tokenizer Class: {type(tokenizer)}")

# Check for specific attributes
attributes_to_check = ['lang_code_to_id', 'get_lang_id', 'src_lang', 'tgt_lang', 'additional_special_tokens']
for attr in attributes_to_check:
    print(f"DEBUG: Has {attr}: {hasattr(tokenizer, attr)}")

# Try to get the ID for Hindi
try:
    print(f"DEBUG: hin_Deva ID: {tokenizer.convert_tokens_to_ids('hin_Deva')}")
except Exception as e:
    print(f"DEBUG: convert_tokens_to_ids error: {e}")

# Check if it has a way to get the lang Id
if hasattr(tokenizer, 'get_lang_id'):
    print(f"DEBUG: get_lang_id('hin_Deva'): {tokenizer.get_lang_id('hin_Deva')}")

# Try to see where the lang codes are stored
if hasattr(tokenizer, 'lang_code_to_id'):
    print(f"DEBUG: lang_code_to_id type: {type(tokenizer.lang_code_to_id)}")
    print(f"DEBUG: hin_Deva in lang_code_to_id: {'hin_Deva' in tokenizer.lang_code_to_id}")

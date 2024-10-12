import time
import os
from openai import OpenAI
from collar.system_settings import SYSTEM_MESSAGE
from collar import utils

OPENAI_BASE_URL = ""
OPENAI_API_KEY = ""
OPENAI_MODEL_NAME = ""

def read_response(file_name):
    logs_dir = cfg_path = os.path.expanduser('~/llm_logs')
    file_path = os.path.join(logs_dir,file_name)
    return utils.read_file_content(file_path)

def save_prompt(method, prompt):
    '''DF
保存prompt到文件。
目录是一个当前目录下的llm_logs目录。
文件名是method 这个ast function def对象的名字 + 一个不包括年份时间信息，比如"10_11_05_05_05" + ”.prompt"'''
    logs_dir = os.path.expanduser('~/llm_logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    method_name = method.name
    timestamp = time.strftime('%m_%d_%H_%M_%S')
    file_name = f'{method_name}_{timestamp}.prompt'
    file_path = os.path.join(logs_dir, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(prompt)
def save_response(method, response):
    '''DF
保存prompt到文件。
目录是一个当前目录下的llm_logs目录。
文件名是method 这个ast function def对象的名字 + 一个不包括年份时间信息，比如"10_11_05_05_05" + ”.response"'''
    logs_dir = os.path.expanduser('~/llm_logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    method_name = method.name
    current_time = time.strftime('%m_%d_%H_%M_%S')
    file_name = f'{method_name}_{current_time}.response'
    file_path = os.path.join(logs_dir, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(response)


def call_llm(method, prompt):
    save_prompt(method, prompt)
    #return read_response("retrieve_10_11_13_58_56.response")
    str_key = OPENAI_API_KEY
    client = OpenAI(api_key=str_key, base_url="https://api.siliconflow.cn/v1")
    start_time=time.time()
    response = client.chat.completions.create(
        model=OPENAI_MODEL_NAME, 
        messages=[{'role': 'system', 
                   'content': f"{SYSTEM_MESSAGE}"}, 
                   {'role': 'user', 'content': prompt}],
                   stream=False, 
                   temperature=0, 
                   max_tokens=4096, 
                   top_p=0.7,
                   frequency_penalty=0.0,
                   presence_penalty=0.0)
    endtime= time.time()
    print(f"Call {OPENAI_MODEL_NAME}:{endtime-start_time} seconds")
    content = response.choices[0].message.content.strip()
    save_response(method, content)
    return content
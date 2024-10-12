
from collar.core.ast.JSource import JSource
from collar.core.ast.PSource import PSource
from collar.core.ast.JMapper import JMapper
from collar.core.ast import Source as src
import collar.method_settings as method_st
import collar.module_setting as module_st
from collar.llm import call_llm
import re

from collar.utils import write_file_content,read_file_content

class Handler:

    def __init__(self, file_path, target_name = "", optional_args=[]):
        self.file_path = file_path
        self.target_name = target_name
        self.optional_args = optional_args
    def save(self):
        write_file_content(self.file_path, self.source.unparse())

    def process_file(self):
        """
        处理单个文件
        :param file_path: 文件路径
        """
        if self.file_path.endswith(".java"):
            if self.file_path == "/Users/dinghaitao/vs_projecty/Install_test/itsm-woms/src/main/java/com/aie/itsm/woms/service/order/impl/OrderInstanceServiceImpl.java":
                print("yes")
            if self.file_path.endswith("Mapper.java"):
                self.source = JMapper(self.file_path)
            else:
                self.source = JSource(self.file_path)
            if self.source.cu == None:
                return
        elif self.file_path.endswith(".py"):
            #self.source = PSource(self.file_path)
            pass
        source = self.source
        # to be done with top doc, the design doc for for the whole file
        body_list = source.body
        for node in body_list:
            if isinstance(node, src.ClassDef):
                self.process_class(node)
            if isinstance(node, src.MethodDef):
                if node.class_obj:
                    continue
                self.process_method(node)
        if self.source.changed:
            self.save()

    def process_class(self, node):
        body_list = node.body
        for node in body_list:
            if isinstance(node, src.MethodDef):
                self.process_method(node)

    def process_method(self, node):
        action = node.action
        if action:
            result = self.generate_code(node)
            if action == "-DOC":
                new_code = result['text']
                self.source.replace_method_doc(node, new_code)
            elif action == "-DES":
                new_code = result['text']
                self.source.replace_design_doc(node, new_code)
            else:
                if "java" in result:
                    new_code = result['java']
                elif "python" in result:
                    new_code = result['python']
                elif "xml" in result:
                    new_code = result['xml']
                else:
                    new_code = result['text']
                self.source.replace_code(node, new_code)
        elif '--force_gen_doc' in self.optional_args:
            result = self.generate_code(node)
            new_code = result['text']
            self.source.replace_method_doc(node, new_code)

    def generate_code(self, method):
        """
        使用OpenAI生成代码
        :param method: 方法的对象
        :param context: 上下文内容
        :return: 生成的代码
        """
        print(f"Handling {method.name}, Action:{method.action}")
        action = method.action
        if action == '-DES' or action == '-DOC':
            str_method_def = method.str_code
        else:
            str_method_def = method.def_string
        method_doc = method.design_doc
        action = method.action
        info = extract_xml_info(method_doc, 'info')
        context = self.build_context()
        if action == '-CODE' or action == '-DES' or action == '-DOC':
            prompt = method_st.Prompt[action].format(context=context, method_info=str_method_def)
        elif action == '-MOD':
            prompt = method_st.Prompt[action].format(context=context, method_info=str_method_def, change_info=info)
        else:
            return ''
        content = call_llm(method, prompt)
        result = extract_code_from_string(content)
        return result


    def build_context(self):
        file_path = self.file_path
        context = 'import的模块的相关方法定义:'
        context += self.source.get_module_def_from_imports() + "\n"
        context += self.source.get_extra_def() + "\n"
        context += '\n当前模块\n' + self.source.read_def_from_module() + "\n"
        return context

def extract_xml_info(content, key):
    """
[功能说明]: 从一个字符串中提取出类似XML的一个元素的信息。例如，从字符串中提取出 `<information>这是我想要的信息</information>` 中的 "这是我想要的信息"。

[设计思想]: 该方法通过正则表达式来匹配并提取字符串中的XML元素信息。首先，定义一个正则表达式模式，该模式匹配以 `<key>` 开始，以 `</key>` 结束的元素，并捕获其中的内容。然后，使用 `re.search` 方法在输入字符串中查找匹配项。如果找到匹配项，则返回捕获的内容并去除前后空格；如果没有找到匹配项，则返回 `None`。

[实现步骤]:
1. 定义一个正则表达式模式，该模式匹配以 `<key>` 开始，以 `</key>` 结束的元素，并捕获其中的内容。
2. 使用 `re.search` 方法在输入字符串中查找匹配项。
3. 如果找到匹配项，则返回捕获的内容并去除前后空格。
4. 如果没有找到匹配项，则返回 `None`。

:param content: 输入的字符串。
:param key: XML元素的标签名。

:return: 提取的XML元素信息，如果没有找到匹配项则返回 `None`。"""
    pattern = re.compile(f'<{key}>(.*?)</{key}>', re.DOTALL)
    match = pattern.search(content)
    if match:
        return match.group(1).strip()
    return None
def extract_code_from_string(input_string):
    """
    从字符串中抽取出代码块
    :param input_string: 输入的字符串
    :return: 抽取出的代码块
    """
    patterns = {'python':'```python\\n(.*?)```',
                'java':'```java\\n(.*?)```',
                'text':'```plaintext\\n(.*?)```',
                 'xml':'```xml\\n(.*?)```'
    }
    result={}
    for k in patterns.keys():
        p = patterns[k]
        match = re.search(p, input_string, re.DOTALL)
        if match:
            result[k] = match.group(1).strip()
    if len(result)==0:
        result['text'] = input_string
    return result
        
def read_def_from_module_file(file_name):
    if file_name.endswith(".java"):
        source = JSource(file_name)
    elif file_name.endswith(".py"):
        source = PSource(file_name)
    else:
        return read_file_content(file_name)
    return source.read_def_from_module()
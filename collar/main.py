"""
这是一个通过调用LLM来实现自动生成代码的模块"""
import os
import ast
import sys
import re
import jpype
import collar.method_settings as method_st
from collar.llm import call_llm
from collar.core.handler.Handler import Handler
import collar.llm as llm
from collar import utils
PROJECT_DIR = os.getenv('PROJECT_DIR')

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

def build_context_from_model(file_name):
    """DF
根据传入的文件名，用AST解析这个文件，读取变量，方法的定义，拼接成一个字符串返回。
字符串的第一句话是这个model的全名，doc， 然后跟上变量的定义和doc，然后是方法的签名。"""
    full_path = get_full_path(file_name)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise FileNotFoundError(f'File not found: {full_path}')
    with open(full_path, 'r', encoding='utf-8') as file:
        file_content = file.read()
    tree = ast.parse(file_content)
    doc_string = ast.get_docstring(tree, clean=True)
    if not doc_string:
        doc_string = ''
    context = f'\n{file_name}:\n{doc_string}\n'
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            context += f'{ast.unparse(node)}\n'
        if isinstance(node, ast.ClassDef):
            context += f'{ast.unparse(node)}\n'
        if isinstance(node, ast.Assign):
            context += f'{ast.unparse(node)}\n'
        if isinstance(node, ast.FunctionDef):
            context += get_method_definition_and_doc(node) + '\n'
    return context

def is_local_import(pkgs):
    """
参数pkgs是一个import的声明，比如utils.time.create_new_time
PROJECT_DIR是全局变量，指示了某一个项目的跟目录。
请用pkgs这个字符串，分解后的每个目录，来匹配项目目录下的文件夹和python文件，
直到找到了这个pkgs对应的python文件，则返回文件名。
如果没有能够匹配上，则返回None"""
    parts = pkgs.split('.')
    current_path = PROJECT_DIR
    for part in parts:
        current_path = os.path.join(current_path, part)
        if os.path.exists(current_path):
            if os.path.isdir(current_path):
                continue
            else:
                current_path += '.py'
                if not os.path.exists(current_path):
                    return None
                if os.path.isfile(current_path):
                    return current_path
        else:
            current_path += '.py'
            if not os.path.exists(current_path):
                return None
            if os.path.isfile(current_path):
                return current_path
            return None
    return None

def build_context_from_import_list(import_list):
    """
[功能说明]: 根据传入的AST import 对象列表，返回对应的model或者方法，变量的定义，拼装出来的字符串。
1. 过滤import 列表，只保留本地的import model，Python 库里的model排除掉。
2. 获取model的内部所有方法的定义，也就是说从ast.FunctionDef对象中获取方法的签名（定义部分）。
3. 如果import的是一个方法，则只获得这个方法的签名。

[设计思想]: 该方法通过遍历传入的AST import 对象列表，过滤出本地的import model。并获取这些model的内部方法定义。对于每个import对象，检查其类型，如果是模块，则获取模块内部所有方法的签名；如果是方法，则只获取该方法的签名。
重要规则：
获取定义时，请使用AST,不要使用sys.modules[import]来装载model或者method来获得相关的定义.
可以调用get_method_signature， 来获取方法的签名。

[实现步骤]:
1. 遍历传入的AST import 对象列表。
2. 通过分析model对应的源文件，是否在本项目目录下或者子目录下，过滤出本地的import model，排除掉其他的model
3. 对于每个本地的import model，通过读取model对应的源文件，获取其内部所有方法的签名。
4. 如果import的是一个方法，通过读取这个方法所在的model的源文件，获取该方法的签名。
5. 将获取到的model或者方法，变量的定义拼装成一个字符串并返回。

:param import_list: 传入的AST import 对象列表。

:return: 拼装出来的字符串，包含对应的model或者方法，变量的定义。"""
    local_imports = set()
    for imp in import_list:
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                file_name = is_local_import(alias.name)
                if file_name:
                    local_imports.add(file_name)
        elif isinstance(imp, ast.ImportFrom):
            file_name = is_local_import(imp.module)
            if not file_name:
                for n in imp.names:
                    file_name = is_local_import(f'{imp.module}.{n.name}')
                    if file_name:
                        local_imports.add(file_name)
            else:
                local_imports.add(file_name)
    context = ''
    for file_name in local_imports:
        context += build_context_from_model(file_name)
    return context

def check_doc_string(doc_string):
    keywords = ['-CODE', '-DOC', '-DES', '-MOD']
    for keyword in keywords:
        if doc_string.startswith(keyword + '\n'):
            return True
    return False

def get_import_list(tree):
    """
[功能说明]: 该方法用于从一个抽象语法树（AST）中提取所有的导入语句，并返回一个包含所有导入语句的列表。

[设计思想]: 该方法通过遍历AST树中的所有节点，并检查节点类型是否为`ast.Import`或`ast.ImportFrom`，来提取所有的导入语句。对于`ast.Import`节点，提取每个别名的导入语句；对于`ast.ImportFrom`节点，提取模块和别名的导入语句。

[实现步骤]:
1. 初始化一个空列表`import_list`，用于存储所有的导入语句。
2. 遍历AST树中的所有节点。
3. 如果节点类型为`ast.Import`，则遍历其别名列表，将每个别名的导入语句格式化为`import <alias.name>`并添加到`import_list`中。
4. 如果节点类型为`ast.ImportFrom`，则将模块和别名的导入语句格式化为`from <node.module> import <alias.name>`并添加到`import_list`中。
5. 返回`import_list`。

:param tree: 抽象语法树（AST）对象。

:return: 包含所有导入语句的列表。"""
    import_list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_list.append(node)
        elif isinstance(node, ast.ImportFrom):
            import_list.append(node)
    return import_list

def extract_code_from_string(input_string):
    """
    从字符串中抽取出代码块
    :param input_string: 输入的字符串
    :return: 抽取出的代码块
    """
    pattern_python = '```python\\n(.*?)```'
    pattern_text = '```plaintext\\n(.*?)```'
    match = re.search(pattern_python, input_string, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        match = re.search(pattern_text, input_string, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            return input_string

def get_full_path(path):
    """
    获取完整路径，如果路径是相对路径，则使用当前执行命令的路径+相对路径
    :param path: 路径
    :return: 完整路径
    """
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    return os.path.abspath(path)

def get_all_python_files(directory):
    """
    获取目录下所有的Python文件
    :param directory: 目录路径
    :return: 所有Python文件的列表
    """
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def read_file_content(file_path):
    """
    读取文件内容
    :param file_path: 文件路径
    :return: 文件内容
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file_content(file_path, content):
    """
    写入文件内容
    :param file_path: 文件路径
    :param content: 文件内容
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def get_method_signature(node):
    """
    从ast.FunctionDef对象中获取方法的签名（定义部分）。
    
    :param node: ast.FunctionDef 对象
    :return: 方法签名的字符串
    """
    if not isinstance(node, ast.FunctionDef):
        raise ValueError('输入节点必须是ast.FunctionDef类型')
    method_name = node.name
    args = node.args
    arg_names = [arg.arg for arg in args.args]
    if args.vararg:
        arg_names.append(f'*{args.vararg.arg}')
    if args.kwarg:
        arg_names.append(f'**{args.kwarg.arg}')
    arg_str = ', '.join(arg_names)
    method_signature = f'def {method_name}({arg_str}):'
    return method_signature

def get_method_definition_and_doc(node):
    """
    获取一个AST方法对象的定义和文档字符串，并组合成一个字符串返回。
    
    :param node: ast.FunctionDef 对象
    :return: 包含方法定义和文档字符串的字符串
    """
    if not isinstance(node, ast.FunctionDef):
        raise ValueError('输入节点必须是ast.FunctionDef类型')
    method_def = get_method_signature(node)
    docstring = ast.get_docstring(node, clean=True)
    if not docstring:
        docstring = ''
    pattern = re.compile('^D[A-Z]\\n')
    matches = pattern.findall(docstring)
    if len(matches) > 0:
        docstring = docstring[3:]
    result = f'\n{method_def}\n{(docstring if docstring else '')}'
    return result

def get_method_code(file_content, method_name):
    """
    获取方法的代码
    :param file_content: 文件内容
    :param method_name: 方法名
    :return: 方法的代码
    """
    tree = ast.parse(file_content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return ast.unparse(node)
    return None

def should_generate_code(method):
    """
    判断是否需要生成代码
    :param method: 方法节点
    :return: 是否需要生成代码
    """
    if method.body == [ast.Pass()] or method.body == [ast.Return(value=None)] or method.body == []:
        if method.body == []:
            return True
        if method.body[0].value is None:
            return True
    return False

def format_doc(doc):
    """
[功能说明]: 该方法用于格式化文档字符串。它会检查文档字符串是否以'D'开头，如果不是，则在开头增加一个换行符。然后，它会将每个换行符后面的行进行Python缩进，并返回格式化后的文档字符串。

[设计思想]: 该方法通过解析文档字符串并进行字符串操作来实现格式化。首先，检查文档字符串是否以'D'开头，如果不是，则在开头增加一个换行符。然后，将文档字符串按换行符分割成多行，并对每行进行缩进处理。最后，将处理后的行重新组合成一个格式化的文档字符串并返回。

[实现步骤]:
1. 检查文档字符串是否以'D'开头，如果不是，则在开头增加一个换行符。
2. 将文档字符串按换行符分割成多行。
3. 对每行进行缩进处理。
4. 将处理后的行重新组合成一个格式化的文档字符串并返回。

:param doc: 需要格式化的文档字符串。

:return: 格式化后的文档字符串。"""
    if not doc.startswith('\n'):
        doc = '\n' + doc
    lines = doc.split('\n')
    formatted_lines = [line.lstrip() for line in lines]
    formatted_doc = '\n'.join(formatted_lines)
    return formatted_doc

def insert_import(tree, import_def):
    """DF
[功能说明]: 该方法用于在抽象语法树（AST）中查找并插入一个导入定义（import_def）。如果导入定义已经存在于AST树中，则不会进行任何操作。

[设计思想]: 该方法通过遍历AST树中的所有节点，检查是否存在与导入定义相同的导入节点。如果不存在，则将导入定义插入到AST树中。

[实现步骤]:
1. 遍历AST树中的所有节点。
2. 检查每个节点是否为`ast.Import`或`ast.ImportFrom`类型。
3. 如果节点是`ast.Import`类型，则检查其别名列表，看是否存在与导入定义相同的别名。
4. 如果节点是`ast.ImportFrom`类型，则检查其模块和别名，看是否存在与导入定义相同的模块和别名。
5. 如果找到与导入定义相同的导入节点，则不进行任何操作。
6. 如果未找到与导入定义相同的导入节点，则将导入定义插入到AST树中。

:param tree: 抽象语法树（AST）对象。
:param import_def: 要插入的导入定义对象。

:return: 无返回值。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == import_def.names[0].name:
                    return
        elif isinstance(node, ast.ImportFrom):
            if node.module == import_def.module and node.names[0].name == import_def.names[0].name:
                return
    tree.body.insert(0, import_def)

class PHandler:

    def __init__(self, file_path, optional_args):
        self.file_path = file_path
        self.optional_args = optional_args
        self.changed = False
        self.tree = None
        self.short_module_name = None

    def save(self):
        write_file_content(self.file_path, ast.unparse(self.tree))

    def process_file(self):
        """
        处理单个文件
        :param file_path: 文件路径
        """
        file_content = read_file_content(self.file_path)
        self.tree = ast.parse(file_content)
        setattr(self.tree, 'file_path', self.file_path)
        file_name = os.path.basename(self.file_path)
        self.short_module_name = os.path.splitext(file_name)[0]
        model_doc = ast.get_docstring(self.tree)
        if model_doc:
            if check_doc_string(model_doc):
                if model_doc.startswith('-DES'):
                    new_doc = self.generate_module_design_with_openai()
                    self.replace_model_code(self.tree, new_doc)
            if self.changed:
                self.save()
                return
        body_list = ast.walk(self.tree)
        for node in body_list:
            if isinstance(node, ast.ClassDef):
                self.process_class(node)
            if isinstance(node, ast.FunctionDef):
                self.process_method(node)
        if self.changed:
            self.save()

    def process_class(self, node):
        body_list = ast.walk(node)
        for node in body_list:
            if isinstance(node, ast.FunctionDef):
                self.process_method(node)

    def process_method(self, node):
        method_doc = ast.get_docstring(node)
        if method_doc:
            if not check_doc_string(method_doc):
                return
            method_doc = ast.get_docstring(node)
            if method_doc.startswith('-CODE'):
                new_code = self.generate_code_with_openai(node)
                self.replace_code(node, new_code)
            if method_doc.startswith('-MOD'):
                new_code = self.generate_code_with_openai(node, 'modify')
                self.replace_code(node, new_code)
            elif method_doc.startswith('-DOC'):
                new_doc = self.generate_doc_with_openai(node)
                self.replace_method_doc(node, new_doc)
            elif method_doc.startswith('-DES'):
                new_doc = self.generate_design_with_openai(node)
                self.replace_method_doc(node, new_doc)
        elif '--force_gen_doc' in self.optional_args:
            new_doc = self.generate_doc_with_openai(node)
            self.replace_method_doc(node, new_doc)

    def generate_code_with_openai(self, method, action='create'):
        """
        使用OpenAI生成代码
        :param method: 方法的对象
        :param context: 上下文内容
        :return: 生成的代码
        """
        str_method_def = get_method_definition_and_doc(method)
        method_doc = ast.get_docstring(method)
        info = extract_xml_info(method_doc, 'info')
        context = self.build_context()
        if action == 'create':
            prompt = method_st.cre_context.format(context=context, method_info=str_method_def)
        elif action == 'modify':
            prompt = method_st.mod_context.format(context=context, method_info=str_method_def, change_info=info)
        else:
            return ''
        content = call_llm(method, prompt)
        content = extract_code_from_string(content)
        return content

    def build_context(self):
        file_path = self.file_path
        context = 'import的模块的相关方法定义:'
        import_list = get_import_list(self.tree)
        context += build_context_from_import_list(import_list)
        context += '\n当前模块\n' + build_context_from_model(file_path)
        return context

    def generate_doc_with_openai(self, method):
        """
        使用OpenAI生成方法的文档
        :param method: 方法的定义对象
        :param context: 上下文内容
        :return: 生成的文档
        """
        context = self.build_context()
        prompt = method_st.doc_context.format(context=context, method_info=ast.unparse(method))
        content = call_llm(method, prompt)
        content = extract_code_from_string(content)
        return content

    def generate_design_with_openai(self, method):
        """
        使用OpenAI生成方法的文档
        :param method: 方法的定义对象
        :param context: 上下文内容
        :return: 生成的文档
        """
        context = self.build_context()
        prompt = method_st.des_context.format(context=context, method_info=ast.unparse(method))
        content = call_llm(prompt)
        content = extract_code_from_string(content)
        return content

    def generate_module_design_with_openai(self):
        """
        使用OpenAI生成方法的文档
        :param method: 方法的定义对象
        :param context: 上下文内容
        :return: 生成的文档
        """
        context = self.build_context()
        req_info = ast.get_docstring(self.tree)
        prompt = method_st.des_model_context.format(context=context, requirement_info=req_info)
        content = call_llm(self.tree, prompt)
        content = extract_code_from_string(content)
        return content

    def replace_method_code(self, method, new_function_def):
        """
        根据提供的新的代码，来替换method原来的代码，但是保留原来的doc.
        如果doc的开始字符是"DC", 那么修改成"DF"
        """
        method.body = [method.body[0]]
        start_from = 0
        if type(new_function_def.body[0]) == ast.Expr:
            start_from = 1
        for body_item in new_function_def.body[start_from:]:
            method.body.append(body_item)
        docstring_node = ast.get_docstring(method)
        if docstring_node:
            if docstring_node.startswith('-CODE'):
                method.body[0].value.value = docstring_node.replace('-CODE', '-DONE', 1)
            elif docstring_node.startswith('-MOD'):
                method.body[0].value.value = docstring_node.replace('-MOD', '-DONE', 1)
        self.changed = True
        return

    def replace_method_doc(self, method, new_doc):
        """
    [功能说明]: 该方法用于替换方法中的文档字符串。如果新的文档字符串以'DC'开头，则将其替换为'DF'。如果方法中已经存在文档字符串，则直接替换；如果不存在，则将新的文档字符串插入到方法的开头。

    [设计思想]: 该方法通过解析AST（抽象语法树）来定位方法的文档字符串，并根据新的文档字符串进行替换。如果新的文档字符串以'DC'开头，则进行相应的替换操作。如果方法中已经存在文档字符串，则直接替换；如果不存在，则将新的文档字符串插入到方法的开头。

    [实现步骤]:
    1. 解析方法的AST树，找到方法的文档字符串节点。
    2. 检查新的文档字符串是否以'DC'开头，如果是，则将其替换为'DF'。
    3. 如果方法中已经存在文档字符串，则直接替换；如果不存在，则将新的文档字符串插入到方法的开头。
    4. 设置全局变量`changed`为`true`，表示文档字符串已成功替换。

    :param method: 要替换文档字符串的方法对象。
    :param new_doc: 新的文档字符串。

    :return: 无返回值。"""
        if new_doc.startswith('-DOC'):
            new_doc = new_doc.replace('-DOC', '-DONE', 1)
        new_doc = format_doc(new_doc)
        docstring_node = ast.get_docstring(method)
        if docstring_node:
            method.body[0].value.value = new_doc
        else:
            docstring_node = ast.Expr(value=ast.Str(s=new_doc))
            method.body.insert(0, docstring_node)
        self.changed = True
        return

    def replace_model_code(self, new_code):
        """-DONE
    用AST来解析new_code，然后把新的tree里的每个对象，一层一层的都添加到原来的tree里。"""
        new_tree = ast.parse(new_code)
        for node in new_tree.body:
            self.tree.body.append(node)
        self.changed = True
        return self.tree

    def replace_code(self, method, new_code):
        """
    [功能说明]: 该方法用于将新的代码插入到AST树中指定的方法中，并替换原有代码。如果新的代码包含导入语句或函数定义，则会相应地更新AST树。

    [设计思想]: 该方法通过解析新的代码并将其插入到指定的方法中来实现。首先，将新的代码解析为AST树，然后遍历新AST树，根据节点类型（导入语句、函数定义等）进行相应的处理。最后，将处理后的节点插入到指定的方法中。

    [实现步骤]:
    1. 将新的代码解析为AST树。
    2. 遍历新AST树，根据节点类型（导入语句、函数定义等）进行相应的处理。
    3. 将处理后的节点插入到指定的方法中。
    4. 如果新的代码包含导入语句或函数定义，则会相应地更新AST树。

    :param tree: 要插入新代码的AST树。
    :param method: 要插入新代码的方法对象。
    :param new_code: 新的代码字符串。

    :return: 无返回值。"""
        new_bodys = ast.parse(new_code).body
        for b in new_bodys:
            if type(b) == ast.Import or type(b) == ast.ImportFrom:
                insert_import(self.tree, b)
            elif type(b) == ast.FunctionDef:
                self.replace_method_code(method, b)

def setup_env():
    """-DONE
当前用户的根目录下的collar.cfg，读取一下变量，如果collar.cfg不存在，则从环境变量读取
从环境变量文件中读取变量:
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL',"https://api.siliconflow.cn/v1")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY',"")
OPENAI_MODEL_NAME = os.getenv('OPENAI_MODEL_NAME',"deepseek-ai/DeepSeek-V2.5")
如果OPENAI_API_KEY 是"",那么打印”请配置OPENAI_API_KEY"，以及说明如何配置的信息 返回False
打印以上三个变量，OPENAI_API_KEY，只保留开头和结尾的3个字符，其他的字符转成*。
然后把这个三个变量设置给llm的全局变量
返回True"""
    cfg_path = os.path.expanduser('~/collar.cfg')
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as f:
            for line in f:
                if line.startswith('OPENAI_BASE_URL'):
                    OPENAI_BASE_URL = line.split('=')[1].strip()
                elif line.startswith('OPENAI_API_KEY'):
                    OPENAI_API_KEY = line.split('=')[1].strip()
                elif line.startswith('OPENAI_MODEL_NAME'):
                    OPENAI_MODEL_NAME = line.split('=')[1].strip()
    else:
        OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.siliconflow.cn/v1')
        OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'sk-qiivfdhwemymhlwzdhajuhigfdkmyalzmigfdhfweveocomy')
        OPENAI_MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'deepseek-ai/DeepSeek-V2.5')
    if not OPENAI_API_KEY:
        content = 'OPENAI_BASE_URL=https://api.siliconflow.cn/v1\nOPENAI_API_KEY=\nOPENAI_MODEL_NAME=deepseek-ai/DeepSeek-V2.5\n'
        utils.write_file_content(cfg_path, content)
        print(f'请配置OPENAI_API_KEY:\n        可以在环境变量里配置OPENAI_BASE_URL，OPENAI_API_KEY，OPENAI_MODEL_NAME。\n        也可以在当前用户的根目录下~/collar.cfg下配置:\n            OPENAI_BASE_URL=\n            OPENAI_API_KEY=\n            OPENAI_MODEL_NAME=\n              ')
        return False
    masked_api_key = OPENAI_API_KEY[:3] + '*' * (len(OPENAI_API_KEY) - 6) + OPENAI_API_KEY[-3:]
    print(f'OPENAI_BASE_URL: {OPENAI_BASE_URL}')
    print(f'OPENAI_API_KEY: {masked_api_key}')
    print(f'OPENAI_MODEL_NAME: {OPENAI_MODEL_NAME}')
    llm.OPENAI_BASE_URL = OPENAI_BASE_URL
    llm.OPENAI_API_KEY = OPENAI_API_KEY
    llm.OPENAI_MODEL_NAME = OPENAI_MODEL_NAME
    return True

def setup_api_key(api_key):
    """-DONE
把传入的api_key保存或者更新到cfg_path配置文件中"""
    cfg_path = os.path.expanduser('~/collar.cfg')
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as file:
            content = file.read()
        content = re.sub('OPENAI_API_KEY=.*', f'OPENAI_API_KEY={api_key}', content)
        with open(cfg_path, 'w') as file:
            file.write(content)
    else:
        with open(cfg_path, 'w') as file:
            file.write(f'OPENAI_BASE_URL=https://api.siliconflow.cn/v1\n')
            file.write(f'OPENAI_API_KEY={api_key}\n')
            file.write(f'OPENAI_MODEL_NAME=deepseek-ai/DeepSeek-V2.5\n')
    print(f"OPENAI_API_KEY已经被更新到配置文件{cfg_path}")

def main():
    """"""
    str_usage = f"Usage: python script.py [--option] [target]')\n    Options:\n        --force: 强制对于模块，类，方法不完整的部分，进行补全。比如一个函数，如果没有Doc，则自动生成Doc,不论是否设置了Action\n    targe: \n        可以是一个目录，Collar会处理目录下（包括子目录）的所有文件\n        可以是一个文件，Collar会处理这个文件\n        可以是文件名:方法名:动作要求\n    Action:\n        -DES:当前是一个最初的情况，下一步是生成设计文档\n        -CRE:生成代码实现。\n        -MOD:根据提供的信息，进行代码的修改和优化，信息放在当前方法的文档中，用<info></info>引用起来\n        -DOC:根据目前的文档和代码实现，按照模板来生成文档。\n        -QA:根据文档和当前的代码，进行质量检查，并给出改进建议\n        -TEST:对当前的方法，生成测试用例\n        -RUN:执行测试\n"
    args = sys.argv[1:]
    optional_args = []
    file_args = []
    for arg in args:
        if arg == '--help':
            print(str_usage)
            return
        elif arg.startswith('-OPENAI_API_KEY'):
            str_arr = arg.split('=')
            if len(str_arr) != 2:
                print('请按正确的参数格式设置API_KEY:\n -OPENAI_API_KEY=xxxxxxx')
                return
            else:
                api_key = str_arr[1]
                setup_api_key(api_key)
                return
        if arg.startswith('--'):
            optional_args.append(arg)
        else:
            file_args.append(arg)
    if not setup_env():
        return
    if len(file_args) == 0:
        print('使用当前目录')
        file_path = os.getcwd()
    else:
        file_path = file_args[0]
    full_path = get_full_path(file_path)
    walk_files(optional_args, full_path)

def check_source_file_type(file_name):
    """-DONE
根据传入的文件名或者目录，来确定当前文件或者目录下的文件，是java 文件还是python文件。"""
    import os

    def get_file_type(file_path):
        _, ext = os.path.splitext(file_path)
        if ext == '.java':
            return 'java'
        elif ext == '.py':
            return 'python'
        return None
    result = {'java': [], 'python': []}
    if os.path.isdir(file_name):
        for root, _, files in os.walk(file_name):
            for file in files:
                file_path = os.path.join(root, file)
                file_type = get_file_type(file_path)
                if file_type:
                    result[file_type].append(file_path)
    else:
        file_type = get_file_type(file_name)
        if file_type:
            result[file_type].append(file_name)
    return result

def walk_files(optional_args, full_path):
    print(f'开始处理目录或文件:{full_path}')
    file_types = check_source_file_type(full_path)
    if len(file_types['java']) > 0:
        print('要出处理的源文件类型为Java')
        start_jvm()
    if os.path.isfile(full_path):
        handler = Handler(full_path, optional_args)
        handler.process_file()
    elif os.path.isdir(full_path):
        java_files = file_types['java']
        for file in java_files:
            handler = Handler(file, optional_args)
            handler.process_file()
    else:
        print(f'无效的路径: {full_path}')
    shut_jvm()

def shut_jvm():
    if jpype.isJVMStarted():
        jpype.shutdownJVM()

def start_jvm():
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_java_parser_lib = [os.path.join(root_path, 'collar_java', 'target', 'classes'), os.path.join(root_path, 'collar_java', 'target', 'java_d2c-1.0-SNAPSHOT.jar')]
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=default_java_parser_lib)
        print(f'JVM 装载完成:{default_java_parser_lib}')

def test_function():
    """-DONE
[功能说明]: 这个方法用于测试当前模块的功能。

[设计思想]: 该方法通过调用其他已定义的方法来验证当前模块的功能是否正常工作。

[实现步骤]:
1. 调用 `process_file` 方法来处理一个示例文件。
2. 调用 `main` 方法来执行主函数，并传入必要的命令行参数。
3. 调用 `test_function` 方法来验证当前模块的功能是否正常工作。

:param args: 命令行参数

:return: 无返回值。

<change_info>请根据Doc 重新编写这个方法</change_info>"""
    main(['example.py'])
    assert True
if __name__ == '__main__':
    main()
from collar.core.ast.Source import Source, decla_list_2_string, remove_c_style_comments, action_keys, startswith_action_key
from collar.core.ast.Source import ImportDef, MethodDef, AssignDef, ClassDef
import traceback
import os, re
import collar.utils as utils
import jpype.imports
from jpype import JClass, JString, JBoolean
Optional = None
MethodDeclaration = None
ClassOrInterfaceDeclaration = None
JavadocComment = None
BlockComment = None

def find_src_path(module_path, file_name):
    """-DONE
根据传入的model,比如com.asiainfo.test
以及这个modle下面的文件路径/user/home/code/src/com/aisinfo/test/Test.java
来找到src的跟目录:/user/home/code/src"""
    module_path_components = module_path.split('.')
    module_path_in_fs = os.path.join(*module_path_components)
    src_root_path = os.path.dirname(file_name)
    while module_path_in_fs !="" and src_root_path.endswith(module_path_in_fs):
        src_root_path = os.path.dirname(src_root_path)
        module_path_in_fs = os.path.dirname(module_path_in_fs)
    return src_root_path

class JSource(Source):

    def unparse(self):
        str_content = str(self.cu.toString())
        return str_content

    def build(self):
        global Optional, MethodDeclaration, ClassOrInterfaceDeclaration, JavadocComment, BlockComment
        Optional = JClass('java.util.Optional')
        MethodDeclaration = JClass('com.github.javaparser.ast.body.MethodDeclaration')
        ClassOrInterfaceDeclaration = JClass('com.github.javaparser.ast.body.ClassOrInterfaceDeclaration')
        JavadocComment = JClass('com.github.javaparser.ast.comments.JavadocComment')
        BlockComment = JClass('com.github.javaparser.ast.comments.BlockComment')
        from ai.d2c import JParserHelper
        try:
            self.cu = JParserHelper.geCompilationUnit(self.file_path)
        except Exception as e:
            traceback.print_exc()
            print(f'Parse file Error:\n                  file name:{self.file_path};\n                  error message:{e}')
            self.cu = None
            return False
        if self.cu == None:
            return False
        cu = self.cu
        if cu.getPackageDeclaration().isPresent():
            packageName = cu.getPackageDeclaration().get().getNameAsString()
        else:
            packageName = ''
        self.module_path = str(packageName)
        self.module_name = self.short_file_name
        self.full_module_name = self.module_path + '.' + self.module_name
        self.src_root_path = find_src_path(self.module_path, self.file_path)
        self.main_path = os.path.dirname(self.src_root_path)
        self.project_path = os.path.dirname(os.path.dirname(os.path.dirname(self.src_root_path)))
        self.class_obj = None
        import_list = cu.getImports()
        self.import_list = []
        for imp in import_list:
            import_obj = JImportDef(decla=imp, source=self)
            self.body.append(import_obj)
            self.import_list.append(import_obj)
        types = cu.getTypes()
        for t in types:
            class_obj = JClassDef(t, self)
            if not self.class_obj:
                self.class_obj = class_obj
            fields = t.getFields()
            for f in fields:
                JAssignDef(f, self, class_obj)
            methods = t.getMethods()
            for m in methods:
                JMethodDef(m, self, class_obj)
        return

    def module_file_in_src_folder(self, module_name):
        """-DONE
module_name是以"."分割的路径，判断module_name是否在root_src_path下面存在"""
        module_path_components = module_name.split('.')
        full_path = os.path.join(self.src_root_path, *module_path_components) + '.java'
        return os.path.exists(full_path)

    def get_extra_def(self):
        return ''

    def get_module_def_from_imports(self):
        str_context = ''
        for imp_obj in self.import_list:
            str_import = imp_obj.name
            if str_import.endswith('*'):
                continue
            if not self.module_file_in_src_folder(str_import):
                continue
            arr_path = str_import.split('.')
            if str_import.find('woms.constants') > -1:
                if not arr_path[-1].endswith('Constants'):
                    arr_path = arr_path[:-1]
            jfile_name = os.path.join(self.src_root_path, *arr_path) + '.java'
            if str_import.find('woms.enums') > -1:
                str_context += utils.read_file_content(jfile_name)
                continue
            source = JSource(jfile_name)
            str_context += source.read_def_from_module()
        return str_context

    def read_def_from_module(self):
        str_context = f'\n{self.full_module_name} \n'
        str_spaces = '    '
        str_double_spaces = '        '
        for decla_obj in self.body:
            if type(decla_obj) == ClassDef:
                str_context += f'{str_spaces}{decla_obj.def_string}\n{str_spaces}'
            if not decla_obj.class_obj:
                str_context += f'\n{decla_obj.def_string}'.replace('\n', '\n' + str_double_spaces)
        str_context += '}\n'
        return str_context

    def replace_code(self, method, new_code):
        return self.replace_method_code(method, new_code)

    def replace_method_code(self, method, new_code):
        try:
            imports_cu, methods_cu = parse_code(new_code)
            self.add_imports(imports_cu)
            self.add_methods(methods_cu)
            method.remove_action_key_in_design_doc()
        except Exception as e:
            traceback.print_exc()
            print(e)
            self.changed = False
            return False

    def add_methods(self, methods_cu):
        if methods_cu == None:
            return
        target_class_opt = self.cu.findFirst(ClassOrInterfaceDeclaration)
        if target_class_opt.isPresent():
            class_decl = target_class_opt.get()
            new_methods = methods_cu.findAll(MethodDeclaration)
            for new_method in new_methods:
                existing_method = find_method_by_signature(class_decl, new_method)
                if existing_method:
                    existing_method.setBody(new_method.getBody().orElse(None))
                    existing_method.setAnnotations(new_method.getAnnotations())
                    if new_method.hasJavaDocComment():
                        existing_method.setJavadocComment(new_method.getJavadocComment().get())
                    existing_method.setType(new_method.getType())
                    existing_method.setModifiers(new_method.getModifiers())
                else:
                    class_decl.addMember(new_method)
            self.changed = True
        else:
            print('No class found in the CompilationUnit.')

    def add_imports(self, imports_cu):
        if imports_cu == None:
            return
        new_imports = imports_cu.getImports()
        for new_import in new_imports:
            if not self.cu.getImports().contains(new_import):
                self.cu.addImport(new_import)
                self.changed = True

    def replace_method_doc(self, method, new_doc):
        indx = new_doc.find('*/')
        if indx != -1:
            new_doc = new_doc[:indx + 2]
        new_doc = remove_c_style_comments(new_doc)
        if new_doc.startswith('-DOC'):
            new_doc = new_doc.replace('-DOC', '-DONE', 1)
        try:
            method.decla.setJavadocComment(new_doc)
            method.design_doc_obj = method.decla.getJavadocComment()
            method.design_doc_string = new_doc
            method.remove_action_key_in_design_doc()
            self.changed = True
            return True
        except Exception as e:
            print(e)
            return False

    def replace_design_doc(self, method, new_doc):
        indx = new_doc.find('*/')
        if indx != -1:
            new_doc = new_doc[:indx + 2]
        new_doc = remove_c_style_comments(new_doc)
        if new_doc.startswith('-DES'):
            new_doc = new_doc.replace('-DES', '-DONE', 1)
        try:
            if type(method.design_doc_obj) == Optional:
                method.decla.setJavadocComment(new_doc)
                method.design_doc_obj = method.decla.getJavadocComment()
            else:
                method.design_doc_obj.setContent(new_doc)
            method.design_doc_string = new_doc
            method.remove_action_key_in_design_doc()
            self.changed = True
            return True
        except Exception as e:
            traceback.print_exc()
            print(e)
            return False

class JAssignDef(AssignDef):

    def build_design_doc_string(self):
        self.design_doc_string = ''
        self.design_doc_obj = None
        pass
    pass

class JMethodDef(MethodDef):

    def build(self):
        super().build()

    def build_def_string(self):
        decla = self.decla
        str_def = ''
        str_decla = str(decla.toString())
        indx = str_decla.find('{')
        if indx > -1:
            str_def = str_decla[:indx]
        else:
            str_def = str_decla
        self.def_string = str_def
        return str_def

    def build_design_doc_string(self):
        decla = self.decla
        self.design_doc_string = ''
        if hasattr(decla, 'hasJavaDocComment') and decla.hasJavaDocComment():
            str_doc = str(decla.getJavadocComment().get().toString())
            str_doc = remove_c_style_comments(str_doc)
            if startswith_action_key(str_doc):
                self.design_doc_string = str_doc
                self.design_doc_obj = decla.getJavadocComment()
        if self.design_doc_string == '':
            all_contained_comments = decla.getAllContainedComments()
            if len(all_contained_comments) > 0:
                comment = all_contained_comments[0]
                str_doc = str(comment.toString())
                str_doc = remove_c_style_comments(str_doc)
                if startswith_action_key(str_doc):
                    self.design_doc_string = str_doc
                    self.design_doc_obj = comment

    def remove_action_key_in_design_doc(self):
        from ai.d2c import JParserHelper
        if not self.design_doc_obj:
            return
        dcs = self.design_doc_string
        for ak in action_keys:
            dcs = dcs.replace(ak + '\n', '', 1)
            dcs = dcs.replace(ak, '', 1)
        if type(self.design_doc_obj) == Optional:
            doc_obj = self.design_doc_obj.get()
            if type(doc_obj) == JavadocComment:
                self.decla.setJavadocComment(dcs)
                return
        if not type(self.design_doc_obj) == BlockComment:
            block_comment = BlockComment(JString(dcs))
            self.design_doc_obj = block_comment
        body = self.decla.getBody().get()
        if len(body.getStatements()) > 0:
            firstStatement = body.getStatements().get(0)
        if dcs == '':
            firstStatement.removeComment()
        else:
            comment_lines = dcs.splitlines()
            indentation = find_indentation_string_after_newline(str(self.decla.toString()))
            formatted_comment = '\n' + '\n'.join((f'{indentation * 2}* {line}' for line in comment_lines)) + f'\n{indentation * 2}'
            firstStatement.setBlockComment(formatted_comment)

class JImportDef(ImportDef):

    def build_design_doc_string(self):
        self.design_doc_string = ''
        self.design_doc_obj = None
        pass

class JClassDef(ClassDef):

    def build(self):
        delca_type = str(type(self.decla))
        if delca_type == "<java class 'com.github.javaparser.ast.body.ClassOrInterfaceDeclaration'>":
            if self.decla.isInterface():
                self.delca_type = 'interface'
            else:
                self.delca_type = 'class'
        elif delca_type == "<java object 'com.github.javaparser.ast.body.AnnotationDeclaration'>":
            self.delca_type = 'annotation'
        elif delca_type == "<java class 'com.github.javaparser.ast.body.EnumDeclaration'>":
            self.delca_type = 'enum'
        else:
            self.delca_type = ''
        super().build()
        self.full_name = self.source.module_name + '.' + self.name
        self.build_signature()

    def build_design_doc_string(self):
        decla = self.decla
        self.design_doc_string = ''
        if hasattr(decla, 'hasJavaDocComment') and decla.hasJavaDocComment():
            str_doc = str(decla.getJavadocComment().get().toString())
            str_doc = remove_c_style_comments(str_doc)
            if startswith_action_key(str_doc):
                self.design_doc_string = str_doc
                self.design_doc_obj = decla.getJavadocComment()
        if self.design_doc_string == '':
            all_contained_comments = decla.getAllContainedComments()
            if len(all_contained_comments) > 0:
                comment = all_contained_comments[0]
                str_doc = str(comment.toString())
                str_doc = remove_c_style_comments(str_doc)
                if startswith_action_key(str_doc):
                    self.design_doc_string = str_doc
                    self.design_doc_obj = comment

    def build_signature(self):
        str_def = ''
        decla = self.decla
        if hasattr(decla, 'getModifiers'):
            str_def += decla_list_2_string(decla.getModifiers())
        str_def += f'{self.delca_type} '
        str_def += f'{self.name} '
        if hasattr(decla, 'getImplementedTypes'):
            str_def += decla_list_2_string(decla.getImplementedTypes())
        self.signature = str_def
        return str_def

def find_method_by_signature(class_decl, new_method):
    """
    根据方法签名在类中查找现有方法（考虑重载）。
    :param class_decl: ClassOrInterfaceDeclaration 对象
    :param new_method: MethodDeclaration 对象
    :return: MethodDeclaration 对象或 None
    """
    try:
        methods = class_decl.getMethodsByName(new_method.getNameAsString())
        for i in range(methods.size()):
            existing_method = methods.get(i)
            if parameters_match(existing_method.getParameters(), new_method.getParameters()):
                return existing_method
        return None
    except Exception as e:
        print(f'Error finding method by signature: {e}')
        return None

def parameters_match(existing_params, new_params):
    """
    比较两个参数列表是否匹配。
    :param existing_params: JavaParser 的 Parameter 列表
    :param new_params: JavaParser 的 Parameter 列表
    :return: 布尔值，表示参数是否匹配
    """
    if existing_params.size() != new_params.size():
        return False
    for i in range(existing_params.size()):
        existing_param = existing_params.get(i)
        new_param = new_params.get(i)
        if not existing_param.getType().equals(new_param.getType()):
            return False
    return True

def parse_code(new_code):
    from ai.d2c import JParserHelper
    imports_cu = None
    methods_cu = None
    code_parts = re.split('(import\\s+[\\w\\.]+\\s*;\\s*)', new_code)
    if len(code_parts) == 1:
        imports = ''
        methods = code_parts[0]
    else:
        imports = code_parts[0]
        methods = ''.join(code_parts[1:])
    has_class_definition = 'class ' in methods
    if has_class_definition:
        methods_cu = JParserHelper.parseCodeBlock(methods)
    else:
        wrapped_code = 'public class DummyClass { ' + new_code + ' }'
        methods_cu = JParserHelper.parseCodeBlock(wrapped_code)
    if imports:
        imports_cu = JParserHelper.parseCodeBlock(imports)
    return (imports_cu, methods_cu)

def find_indentation_string_after_newline(text: str):
    newline_index = text.find('\n')
    if newline_index == -1:
        return None
    after_newline = text[newline_index + 1:]
    indentation = ''
    for char in after_newline:
        if char == ' ' or char == '\t':
            indentation += char
        else:
            break
    return indentation
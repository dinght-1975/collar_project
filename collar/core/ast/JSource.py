from collar.core.ast.Source import Source, decla_list_2_string,remove_c_style_comments
from collar.core.ast.Source import ImportDef, MethodDef, AssignDef, ClassDef
import os
import collar.utils as utils
import jpype.imports

def find_src_path(module_path, file_name):
    """-DONE
根据传入的module_path, 比如com.asia.test
以及传入的当前一个源文件的文件名,比如/user/workspace/src/com/asia/test/MyTest.java
返回src的根目录/usr/workspace/src/"""
    module_components = module_path.split('.')
    file_components = file_name.split(os.path.sep)
    common_prefix = os.path.commonprefix([module_components, file_components])
    common_length = len(common_prefix)
    root_directory = os.path.sep.join(file_components[:-common_length])
    return root_directory

class JSource(Source):

    def unparse(self):
        str_content = str(self.cu.toString())
        return str_content

    def build(self):
        from ai.d2c import JParserHelper
        try:
            self.cu = JParserHelper.geCompilationUnit(self.file_path)
        except Exception as e:
            print(f"""Parse file Error:
                  file name:{self.file_path};
                  error message:{e}""")
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
        self.module_name = self.short_file_name[:-4]
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
                JAssignDef(f,self,class_obj)
            methods = t.getMethods()
            for m in methods:
                JMethodDef(m, self,class_obj)
        return

    def module_file_in_src_folder(self, module_name):
        """-DONE
module_name是以"."分割的路径，判断module_name是否在root_src_path下面存在"""
        module_path_components = module_name.split('.')
        full_path = os.path.join(self.src_root_path, *module_path_components) + '.java'
        return os.path.exists(full_path)

    def get_extra_def(self):
        return ""
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
                str_context += utils.read_file_content (jfile_name)
                continue
            source = JSource(jfile_name)
            str_context += source.read_def_from_module()
        return str_context
    def read_def_from_module(self):
        str_context = f"""\n{self.full_module_name} \n"""
        str_spaces = "    "
        str_double_spaces = "        "
        for decla_obj in self.body:
            if type(decla_obj) == ClassDef:
                str_context += f"{str_spaces}{decla_obj.def_string}\n{str_spaces}"
            if not decla_obj.class_obj:
                str_context += f"\n{decla_obj.def_string}".replace("\n","\n"+str_double_spaces)
        str_context += "}\n"
        return str_context
    
    def replace_code(self, method, new_code):
        return self.replace_method_code(method,new_code)

    def replace_method_code(self,method, new_code):
        from ai.d2c import JParserHelper
        try:
            if JParserHelper.updateMethod(self.cu, new_code):
                self.changed = True 
                return True 
            else:
                return False
        except Exception as e:
            print(e)
            return False
    
    def replace_method_doc(self, method, new_doc):
        indx = new_doc.find("*/")
        if indx != -1:
            new_doc = new_doc[:indx+2]
        new_doc = remove_c_style_comments(new_doc)
        if new_doc.startswith('-DOC'):
            new_doc = new_doc.replace('-DOC', '-DONE', 1)
        try:
                method.decla.setJavadocComment(new_doc)
                self.changed = True 
                return True 
        except Exception as e:
            print(e)
            return False
        
        


class JAssignDef(AssignDef):
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


class JImportDef(ImportDef):
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




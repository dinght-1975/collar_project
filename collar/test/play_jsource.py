
from core.ast.JSource import JSource as Source
import jpype
import jpype.imports
from os import path
from core.handler.Handler import Handler
if __name__ == '__main__':
    root_path =  "/Users/dinghaitao/vs_projecty/d2c"
    default_java_parser_lib = [path.join(root_path,"java","java_d2c","target","classes"),path.join(root_path,"java","java_d2c","target","java_d2c-1.0-SNAPSHOT.jar")]

    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=default_java_parser_lib)
    file_name = "/Users/dinghaitao/vs_projecty/workspace/itsm-woms/src/main/java/com/aie/itsm/woms/service/order/impl/OrderInstanceServiceImpl.java"
    file_name = "/Users/dinghaitao/vs_projecty/d2c/java/java_d2c/src/main/java/ai/d2c/JParserHelper.java"
    handler = Handler(file_name)
    handler.process_file()
    
    jpype.shutdownJVM()

    pass
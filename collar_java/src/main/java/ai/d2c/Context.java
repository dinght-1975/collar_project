package ai.d2c;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

/**
 * ContextBuilder 类用于构建和处理 Java 源文件的上下文信息。
 * 该类提供了从 Java 源文件中提取信息、构建上下文、读取文件内容等功能。
 */
public class Context {

    private static final Logger log = Logger.getLogger(Context.class.getName());
    private static final String PROJECT_PACKAGE_KEYWORD = "com.aie.itsm";

    private static final String PROJECT_PATH = System.getenv("PROJECT_PATH") != null ? System.getenv("PROJECT_PATH")
            : "/Users/dinghaitao/vs_projecty/workspace/itsm-woms";

    private static final String SOURCE_ROOT_PATH = Paths.get(PROJECT_PATH, "src").toString();
    private static final String JAVA_SRC_PATH = Paths.get(SOURCE_ROOT_PATH, "main", "java").toString();
    private static final String RESOURCE_PATH = Paths.get(SOURCE_ROOT_PATH, "main", "resources").toString();
    private static final String TEST_PATH = Paths.get(SOURCE_ROOT_PATH, "test").toString();

    private static String SYSTEM_CONTEXT = null;

    /**
     * 从指定文件中读取内容。
     *
     * @param fileName 文件名
     * @return 文件内容，如果文件不存在则返回空字符串
     */
    public static String readContextFromFile(String fileName) {
        if (!new File(fileName).exists()) {
            log.severe("File " + fileName + " doesn't exist");
            return "";
        }
        try {
            return new String(Files.readAllBytes(Paths.get(fileName)));
        } catch (IOException e) {
            log.severe("Error reading file " + fileName + ": " + e.getMessage());
            return "";
        }
    }

    /**
     * 从 Java 源文件构建上下文信息。
     *
     * @param jsource Java 源文件对象
     * @return 构建的上下文信息
     */
    public static String buildContextFromClass(JSource jsource) {
        // 获取包名和类名
        Map<String, Object> classInfo = (Map<String, Object>) jsource.getCtree().get("class");
        String packageName = (String) jsource.getCtree().get("package");
        String className = (String) classInfo.get("name");
        String classDef = (String) classInfo.get("def");

        StringBuilder strContext = new StringBuilder();
        strContext.append("\n").append(packageName).append(".").append(className).append(" \n")
                .append(classDef).append("\n{\n");

        // 处理字段
        List<Map<String, Object>> fields = (List<Map<String, Object>>) jsource.getCtree().get("fields");
        for (Map<String, Object> field : fields) {
            strContext.append("   ").append(field.get("def")).append("\n");
        }

        // 处理方法
        List<Map<String, Object>> methods = (List<Map<String, Object>>) jsource.getCtree().get("methods");
        for (Map<String, Object> method : methods) {
            strContext.append("   ").append(method.get("def")).append("\n");
        }

        strContext.append("}\n");
        return strContext.toString();
    }

    /**
     * 从指定文件名构建上下文信息。
     *
     * @param fileName 文件名
     * @return 构建的上下文信息
     */
    public static String buildContextFromClassByFile(String fileName) {
        JSource jsource = new JSource(fileName);
        return buildContextFromClass(jsource);
    }

    /**
     * 构建通用上下文信息。
     *
     * @param jsource Java 源文件对象
     * @return 构建的通用上下文信息
     */
    public static String buildCommonContext(JSource jsource) {
        String pathName = jsource.getFileName();
        StringBuilder strContext = new StringBuilder();
        while (true) {
            pathName = new File(pathName).getParent();
            if (pathName == null) {
                break;
            }
            String tail = new File(pathName).getName();
            if (tail.endsWith(".java")) {
                String contextFile = Paths.get(pathName, tail.substring(0, tail.length() - 4) + "ctt").toString();
                if (new File(contextFile).exists()) {
                    strContext.append(readContextFromFile(contextFile)).append("\n");
                }
            }
            String contextFile = Paths.get(pathName, "package.ctt").toString();
            if (new File(contextFile).exists()) {
                strContext.append(readContextFromFile(contextFile)).append("\n");
            }
            if (tail.equals(PROJECT_PATH)) {
                break;
            }
        }
        return strContext.toString();
    }

    /**
     * 构建 Mapper XML 上下文信息。
     *
     * @param jsource Java 源文件对象
     * @return 构建的 Mapper XML 上下文信息
     */
    public static String buildMapperXmlContext(JSource jsource) {
        if (!jsource.isMapper()) {
            return "";
        }
        String xmlFileName = jsource.getMapperXmlFileName();
        if (!new File(xmlFileName).exists()) {
            log.severe("File " + xmlFileName + " doesn't exist.");
            return "";
        }
        String content = readContextFromFile(xmlFileName);
        return "数据库表的定义:\n" + content;
    }

    /**
     * 获取当前类的上下文信息。
     *
     * @param jsource Java 源文件对象
     * @param jmethod 方法对象
     * @return 当前类的上下文信息
     */
    public static String getThisClassAsContext(JSource jsource, Map<String, Object> jmethod) {
        StringBuilder strContext = new StringBuilder("下面是当前这个类的定义:\n");
        strContext.append(buildContextFromClass(jsource));
        return strContext.toString();
    }

    /**
     * 构建表上下文信息。
     *
     * @param jsource Java 源文件对象
     * @return 构建的表上下文信息
     */
    public static String buildTableContext(JSource jsource) {
        if (!jsource.isMapper()) {
            return "";
        }
        String strPackage = (String) jsource.getCtree().get("package");
        String[] arrStrs = strPackage.split("\\.");
        String lastNode = arrStrs[arrStrs.length - 1];
        String ddlFileName = Paths.get(PROJECT_PATH, "sql", "DDL", lastNode + ".init.sql").toString();
        if (!new File(ddlFileName).exists()) {
            log.severe("File " + ddlFileName + " doesn't exist.");
            return "";
        }
        String content = readContextFromFile(ddlFileName);
        return "数据库表的定义:\n" + content;
    }

    /**
     * 构建系统上下文信息。
     *
     * @param role 角色（如 "developer"）
     * @return 构建的系统上下文信息
     */
    public static String buildSystemContext(String role) {
        if (SYSTEM_CONTEXT != null) {
            return SYSTEM_CONTEXT;
        }
        String fileName = Paths.get(PROJECT_PATH, role + ".ctt").toString();
        SYSTEM_CONTEXT = readContextFromFile(fileName);
        return SYSTEM_CONTEXT;
    }

    /**
     * 从导入的类中构建上下文信息。
     *
     * @param jsource Java 源文件对象
     * @return 构建的导入类上下文信息
     */
    public static String buildContextsFromImports(JSource jsource) {
        StringBuilder strContext = new StringBuilder(
                "以下是你将要开发的方法所在的类 " + jsource.getCtree().get("class") + " 所引入的外部重要类库。你正要开发的方法，会使用这类类库里定义的方法和变量。");
        for (Map<String, Object> jimport : (List<Map<String, Object>>) jsource.getCtree().get("imports")) {
            String strImport = (String) jimport.get("name");
            if (strImport.endsWith("*")) {
                continue;
            }
            if (!strImport.contains(PROJECT_PACKAGE_KEYWORD)) {
                continue;
            }
            String[] arrPath = strImport.split("\\.");
            if (strImport.contains("woms.constants")) {
                if (!arrPath[arrPath.length - 1].endsWith("Constants")) {
                    arrPath = java.util.Arrays.copyOf(arrPath, arrPath.length - 1);
                }
            }
            String jfileName = Paths.get(JAVA_SRC_PATH, arrPath).toString() + ".java";
            if (strImport.contains("woms.enums")) {
                strContext.append(readContextFromFile(jfileName));
                continue;
            }
            strContext.append(buildContextFromClassByFile(jfileName));
        }
        return strContext.toString();
    }

    /**
     * 从方法的设计文档中构建上下文信息。
     *
     * @param jsource Java 源文件对象
     * @param jmethod 方法对象
     * @return 构建的设计文档上下文信息
     */
    public static String buildRequestContextFromDD(JSource jsource, Map<String, Object> jmethod) {
        String strMethodNoComment = Util.removeComments((String) jmethod.get("def"));
        if (((String) jmethod.get("req_type")).equals("C")) {
            if (jsource.isMapper()) {
                return "请根据下面的设计，编写方法<" + strMethodNoComment + "> 对应的XML查询定义:\n" + jmethod.get("d_block");
            } else {
                return "请根据下面的设计，编写方法<" + strMethodNoComment + "> 的实现:\n" + jmethod.get("d_block");
            }
        } else if (((String) jmethod.get("req_type")).equals("D")) {
            return "请根据这个代码的实现，以及上面相关的代码，编写这个方法的Java Doc 文档: \n" + jmethod.get("decla").toString();
        }
        return "";
    }

    /**
     * 构建完整的上下文信息。
     *
     * @param jsource Java 源文件对象
     * @param jmethod 方法对象
     * @return 构建的完整上下文信息
     */
    public static Map<String, String> buildContext(JSource jsource, Map<String, Object> jmethod) {
        Map<String, String> contexts = new HashMap<>();
        contexts.put("system_context", buildSystemContext("developer"));
        contexts.put("import_context", buildContextsFromImports(jsource));
        contexts.put("common_context", buildCommonContext(jsource));
        contexts.put("this_class_context", getThisClassAsContext(jsource, jmethod));
        contexts.put("table_context", buildTableContext(jsource));
        contexts.put("mapper_xml_context", buildMapperXmlContext(jsource));
        return contexts;
    }

    public static String buildPrompt(JSource jsource, Map<String, Object> jmethod) {
        Map<String, String> contexts = buildContext(jsource, jmethod);
        String requestStr = buildRequestContextFromDD(jsource, jmethod);
        String str_context = contexts.get("system_context") + "\n\n" +
                contexts.get("import_context") + "\n\n" +
                contexts.get("table_context") + "\n\n" +
                contexts.get("mapper_xml_context") + "\n\n" +
                contexts.get("this_class_context") + "\n\n" +
                contexts.get("common_context") + "\n\n" +
                requestStr + "\n\n";
        return str_context;
    }

}

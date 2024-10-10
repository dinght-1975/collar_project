package ai.d2c;

import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.*;
import com.github.javaparser.ast.ImportDeclaration;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class JSource {

    private String fileName;
    private boolean changed;
    private Map<String, Object> ctree;
    private Boolean isServiceValue;
    private Boolean isMapperValue;
    private String projectPath;
    private CompilationUnit cu;

    public JSource(String fileName) {
        this.fileName = fileName;
        this.changed = false;
        this.ctree = new HashMap<>();
        this.isServiceValue = null;
        this.isMapperValue = null;
        this.projectPath = getProjectPath(fileName);
        buildCtree();
    }

    public boolean isService() {
        if (isServiceValue != null) {
            return isServiceValue;
        }
        String pck = (String) ctree.get("package");
        Pattern pattern = Pattern.compile("^com\\.aie\\.itsm\\.woms\\.service\\.[a-zA-Z_]+\\.impl$");
        Matcher matcher = pattern.matcher(pck);
        isServiceValue = matcher.matches();
        return isServiceValue;
    }

    public boolean isMapper() {
        if (isMapperValue != null) {
            return isMapperValue;
        }
        String pck = (String) ctree.get("package");
        Pattern pattern = Pattern.compile("^com\\.aie\\.itsm\\.woms\\.mapper\\.[a-zA-Z_]+$");
        Matcher matcher = pattern.matcher(pck);
        isMapperValue = matcher.matches();
        return isMapperValue;
    }

    public boolean save() {
        try {
            if (changed == false){
                return false;
            }
            JParserHelper.save(cu, fileName.substring(0, fileName.length() - 4) + "gen");
        } catch (IOException e) {
            e.printStackTrace();
            return false;
        }
        return true;
    }

    public boolean updateMapperXml(String strCode) {
        String fileName = getMapperXmlFileName();
        return Util.updateXMLByElement(fileName, strCode, ctree.get("package") + "." + ctree.get("class.name"));
    }

    public boolean updateMethods(String strCode) {
        if (isMapper()) {
            return updateMapperXml(strCode);
        }
        try {
            if (JParserHelper.updateMethod(cu, strCode)) {
                changed = true;
                return true;
            } else {
                return false;
            }
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    public String getMapperXmlFileName() {
        String strPackage = (String) ctree.get("package");
        String strClassName = (String) ctree.get("class.name");
        String[] arrStrs = strPackage.split("\\.");
        String lastNode = arrStrs[arrStrs.length - 1];
        String[] relativePaths = { "src", "main", "resources", "mapper", lastNode };
        String xmlFileName = String.join(File.separator, relativePaths) + File.separator + strClassName + ".xml";
        return xmlFileName;
    }

    private void buildCtree() {
        ctree = new HashMap<>();
        cu = JParserHelper.geCompilationUnit(fileName);
        if (cu.getPackageDeclaration().isPresent()) {
            ctree.put("package", cu.getPackageDeclaration().get().getNameAsString());
        } else {
            ctree.put("package", "");
        }
        ctree.put("imports", convertDeclaListToMap(cu.getImports()));
        ctree.put("types", convertDeclaListToMap(cu.getTypes()));
        TypeDeclaration<?> classObj = cu.getTypes().get(0);
        ctree.put("class", convertDeclaToMap(classObj));
        ctree.put("fields", convertDeclaListToMap(classObj.getFields()));
        ctree.put("methods", convertDeclaListToMap(classObj.getMethods()));
    }

    public static Map<String, Object> convertDeclaToMap(Object decla) {
        Map<String, Object> obj = new HashMap<>();
        String declaType = decla.getClass().getSimpleName();
        
        // 设置 decla_type 字段
        switch (declaType) {
            case "FieldDeclaration":
                obj.put("decla_type", "field");
                break;
            case "MethodDeclaration":
                obj.put("decla_type", "method");
                break;
            case "ImportDeclaration":
                obj.put("decla_type", "import");
                break;
            case "ClassOrInterfaceDeclaration":
                obj.put("decla_type", "class");
                break;
            case "AnnotationDeclaration":
                obj.put("decla_type", "anno");
                break;
            default:
                obj.put("decla_type", declaType);
                break;
        }

        // 处理名称
        if (decla instanceof MethodDeclaration) {
            obj.put("name", ((MethodDeclaration) decla).getNameAsString());
        } else if (decla instanceof FieldDeclaration) {
            FieldDeclaration field = (FieldDeclaration) decla;
            if (!field.getVariables().isEmpty()) {
                obj.put("name", field.getVariables().get(0).getNameAsString());
            } else {
                obj.put("name", "");
            }
        } else if (decla instanceof ClassOrInterfaceDeclaration) {
            ClassOrInterfaceDeclaration classDecl = (ClassOrInterfaceDeclaration) decla;
            obj.put("name", classDecl.getNameAsString());
            obj.put("class_type", classDecl.isInterface() ? "interface" : "class");
        } else if  (decla instanceof ImportDeclaration) {
            ImportDeclaration importDecl = (ImportDeclaration) decla;
            obj.put("name", importDecl.getNameAsString());
        }

        // 处理方法和类定义及文档注释（模拟 Python 中的 build_def 和 remove_c_style_comments）
        String strDef = "";
        String strDD = "";
        obj.put("req_type","");
        if (obj.get("decla_type").equals("class")) {
            strDef = buildDefForClass((ClassOrInterfaceDeclaration) decla, obj);
            //strDD = removeCStyleComments(getDdFromMethod(decla.toString()));
        } else if (obj.get("decla_type").equals("method")) {
            strDef = buildDefForMethod((MethodDeclaration) decla, obj);
            String methodString = decla.toString();
            strDD = Util.removeCStyleComments(getDdFromMethod(methodString));
            setReqType(obj, strDD, methodString);
        } else {
            strDef = decla.toString();
        }
        obj.put("def", strDef);
        obj.put("d_block", strDD);
        obj.put("decla", decla);

        return obj;
    }

    private static void setReqType(Map<String, Object> obj, String strDD, String methodString) {
        if (!strDD.isEmpty()){
            if (methodString.indexOf("/*DC") >= 0){
                obj.put("req_type","C");
            }else if (methodString.indexOf("/*DM") >= 0){
                obj.put("req_type","M");
            }else if (strDD.indexOf("/*DQ") >= 0){
                obj.put("req_type","Q");
            }else if (methodString.indexOf("/*DD") >= 0){
                obj.put("req_type","D");
            }else if (methodString.indexOf("/*DT") >= 0){
                obj.put("req_type","T");
            }else if (methodString.indexOf("/*DR") >= 0){
                obj.put("req_type","R");
            }else if (methodString.indexOf("/*DB") >= 0){
                obj.put("req_type","B");
            }else{
                obj.put("req_type","N");
            }
        }else{
            obj.put("req_type","");
        }
    }

    public List<Map<String, Object>> convertDeclaListToMap(List<?> declaList) {
        List<Map<String, Object>> ret = new ArrayList<>();

        for (Object decla : declaList) {
            Map<String, Object> obj = convertDeclaToMap(decla);
            ret.add(obj);
        }

        return ret;
    }


    // 将方法体中的 /*DD ... */ 提取出来
    public static String getDdFromMethod(String strBody) {
        String strDd = "";
        int indx = strBody.indexOf("/*D");
        if (indx == -1) {
            return "";
        }
        String strTmp = strBody.substring(indx);
        indx = strTmp.indexOf("*/");
        if (indx == -1) {
            return "";
        }
        strDd = strTmp.substring(0, indx + 2);
        return strDd;
    }

    // 构建方法定义
    public static String buildDefForMethod(MethodDeclaration decla, Map<String, Object> obj) {
        String strDef = "";
        String strDecla = decla.toString();
        int indx = strDecla.indexOf("{");
        if (indx > -1) {
            strDef = strDecla.substring(0, indx);
        } else {
            strDef = strDecla;
        }
        return strDef;
    }

    // 构建类定义
    public static String buildDefForClass(ClassOrInterfaceDeclaration decla, Map<String, Object> obj) {
        String strDef = "";
        
        // 如果有修饰符，拼接它们
        if (decla.getModifiers() != null) {
            strDef = declaListToString(decla.getModifiers(), strDef);
        }
        
        // 拼接类类型和名称
        strDef += obj.get("class_type") + " ";
        strDef += obj.get("name") + " ";

        // 如果有实现的接口或父类，拼接它们
        if (decla.getImplementedTypes() != null) {
            strDef = declaListToString(decla.getImplementedTypes(), strDef);
        }

        return strDef;
    }

    // 将声明列表转换为字符串
    public static String declaListToString(List<?> dlist, String strDef) {
        if (dlist == null) {
            return strDef;
        }
        for (Object m : dlist) {
            strDef += m.toString() + " ";
        }
        return strDef;
    }


    private String getProjectPath(String fileName) {
        File file = new File(fileName);
        while (true) {
            File parent = file.getParentFile();
            if (parent == null) {
                return "";
            }
            if (parent.getName().equals("src")) {
                return parent.getAbsolutePath();
            }
            file = parent;
        }
    }

    public Map<String, Object> getCtree() {
        return ctree;
    }

    public String getFileName() {
        return fileName;
    }
}

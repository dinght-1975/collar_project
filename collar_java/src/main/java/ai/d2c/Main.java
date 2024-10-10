package ai.d2c;

import java.io.FileNotFoundException;
import java.util.Map;
import java.util.List;

public class Main {
    public static void main(String[] args) throws FileNotFoundException {
        String file_name = "/Users/dinghaitao/vs_projecty/workspace/itsm-woms/src/main/java/com/aie/itsm/woms/service/order/impl/OrderInstanceServiceImpl.java";
        // Map<String, Object> result = JParserHelper.parseJavaFile(file_name);
        // System.out.println(result);
        // play_update_method();
        play_context();
    }

    private static void play_context() {
        String fileName = "/Users/dinghaitao/vs_projecty/workspace/itsm-woms/src/main/java/com/aie/itsm/woms/service/order/impl/OrderInstanceServiceImpl.java";
        JSource jSource = new JSource(fileName);
        List<?> jmethods = (List<?>) jSource.getCtree().get("methods");
        Map<String, Object> jmethod = (Map<String, Object>) jmethods.get(2);
        String promptString = Context.buildPrompt(jSource, jmethod);
        System.out.println(promptString);
    }

    private static void play_jsource() {
        String file_name = "/Users/dinghaitao/vs_projecty/Ticket_Labeler/d2c_projects/itsm-woms/src/main/java/com/aie/itsm/woms/service/order/impl/OrderInstanceServiceImpl.java";
        JSource j = new JSource(file_name);
        System.out.print(j.toString());
    }

}

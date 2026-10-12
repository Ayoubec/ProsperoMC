package org.prosperomc;
import java.util.*;
/** Strict, dependency-free JSON reader/writer for Mojang/loader metadata. */
final class Json {
    static Object parse(String s) {
        return parse(s,false);
    }
    // Fabric's reader accepts literal control characters inside quoted mod
    // descriptions and a leading UTF-8 BOM. Keep launcher/settings JSON strict.
    static Object parseFabric(String s) {
        return parse(s,true);
    }
    private static Object parse(String s,boolean fabric) {
        Parser p=new Parser(s,fabric);
        Object v=p.value(0);
        p.ws();
        if(p.i!=s.length())throw p.bad("trailing input");
        return v;
    }
    @SuppressWarnings("unchecked") static Map<String, Object> obj(Object v) {
        if(!(v instanceof Map))throw new IllegalArgumentException("Expected JSON object");
        return (Map<String, Object>)v;
    }
    @SuppressWarnings("unchecked") static List<Object> arr(Object v) {
        if(v==null)return Collections.emptyList();
        if(!(v instanceof List))throw new IllegalArgumentException("Expected JSON array");
        return (List<Object>)v;
    }
    static String str(Object v) {
        return v==null?"":String.valueOf(v);
    }
    static String text(Map<String, Object> m, String k) {
        return str(m.get(k));
    }
    static String stringify(Object v) {
        StringBuilder b=new StringBuilder();
        write(b, v);
        return b.toString();
    }
    static void write(StringBuilder b, Object v) {
        if(v==null) {
            b.append("null");
            return;
        }
        if(v instanceof Number||v instanceof Boolean) {
            b.append(v);
            return;
        }
        if(v instanceof Map) {
            b.append('{');
            boolean first=true;
            for(Object o:((Map<?, ?>)v).entrySet()) {
                Map.Entry<?, ?> e=(Map.Entry<?, ?>)o;
                if(!first)b.append(',');
                first=false;
                write(b, str(e.getKey()));
                b.append(':');
                write(b, e.getValue());
            }
            b.append('}');
            return;
        }
        if(v instanceof Iterable) {
            b.append('[');
            boolean first=true;
            for(Object o:(Iterable<?>)v) {
                if(!first)b.append(',');
                first=false;
                write(b, o);
            }
            b.append(']');
            return;
        }
        b.append('"');
        for(char c:str(v).toCharArray()) {
            switch(c) {
                case '"':b.append("\\\"");
                break;
                case '\\':b.append("\\\\");
                break;
                case '\n':b.append("\\n");
                break;
                case '\r':b.append("\\r");
                break;
                case '\t':b.append("\\t");
                break;
                default:if(c<32)b.append(String.format("\\u%04x", (int)c));
                else b.append(c);
            }
        }
        b.append('"');
    }
    static final class Parser {
        final String s;
        final boolean fabric;
        int i;
        Parser(String s,boolean fabric) {
            this.s=s;
            this.fabric=fabric;
            if(fabric&&s.startsWith("\uFEFF"))i=1;
        }
        void ws() {
            while(i<s.length()&&" \r\n\t".indexOf(s.charAt(i))>=0)i++;
        }
        IllegalArgumentException bad(String m) {
            return new IllegalArgumentException("Invalid JSON at "+i+": "+m);
        }
        Object value(int depth) {
            if(depth>100)throw bad("nesting limit");
            ws();
            if(i==s.length())throw bad("unexpected end");
            char c=s.charAt(i);
            if(c=='"')return string();
            if(c=='{') {
                i++;
                Map<String, Object> m=new LinkedHashMap<String, Object>();
                ws();
                if(take('}'))return m;
                do {
                    ws();
                    if(i==s.length()||s.charAt(i)!='"')throw bad("object key");
                    String k=string();
                    ws();
                    need(':');
                    if(m.containsKey(k))throw bad("duplicate key");
                    m.put(k, value(depth+1));
                    ws();
                    if(take('}'))return m;
                    need(',');
                }
                while(true);
            }
            if(c=='[') {
                i++;
                List<Object> a=new ArrayList<Object>();
                ws();
                if(take(']'))return a;
                do {
                    a.add(value(depth+1));
                    ws();
                    if(take(']'))return a;
                    need(',');
                }
                while(true);
            }
            if(s.startsWith("true", i)) {
                i+=4;
                return Boolean.TRUE;
            }
            if(s.startsWith("false", i)) {
                i+=5;
                return Boolean.FALSE;
            }
            if(s.startsWith("null", i)) {
                i+=4;
                return null;
            }
            int st=i;
            if(take('-')) {
            }
            if(take('0')) {
            }
            else {
                if(i==s.length()||!digit(s.charAt(i)))throw bad("number");
                while(i<s.length()&&digit(s.charAt(i)))i++;
            }
            if(take('.')) {
                if(i==s.length()||!digit(s.charAt(i)))throw bad("fraction");
                while(i<s.length()&&digit(s.charAt(i)))i++;
            }
            if(i<s.length()&&(s.charAt(i)=='e'||s.charAt(i)=='E')) {
                i++;
                if(i<s.length()&&(s.charAt(i)=='+'||s.charAt(i)=='-'))i++;
                if(i==s.length()||!digit(s.charAt(i)))throw bad("exponent");
                while(i<s.length()&&digit(s.charAt(i)))i++;
            }
            try {
                String n=s.substring(st, i);
                return n.indexOf('.')>=0||n.indexOf('e')>=0||n.indexOf('E')>=0?Double.valueOf(n):Long.valueOf(n);
            }
            catch(NumberFormatException e) {
                throw bad("number");
            }
        }
        boolean digit(char c) {
            return c>='0'&&c<='9';
        }
        boolean take(char c) {
            if(i<s.length()&&s.charAt(i)==c) {
                i++;
                return true;
            }
            return false;
        }
        void need(char c) {
            if(!take(c))throw bad("expected "+c);
        }
        String string() {
            need('"');
            StringBuilder b=new StringBuilder();
            while(i<s.length()) {
                char c=s.charAt(i++);
                if(c=='"')return b.toString();
                if(c<32&&!fabric)throw bad("control character");
                if(c=='\\') {
                    if(i==s.length())throw bad("escape");
                    c=s.charAt(i++);
                    switch(c) {
                        case '"':case '\\':case '/':break;
                        case 'b':c='\b';
                        break;
                        case 'f':c='\f';
                        break;
                        case 'n':c='\n';
                        break;
                        case 'r':c='\r';
                        break;
                        case 't':c='\t';
                        break;
                        case 'u':if(i+4>s.length())throw bad("unicode escape");
                        try {
                            c=(char)Integer.parseInt(s.substring(i, i+4), 16);
                        }
                        catch(NumberFormatException e) {
                            throw bad("unicode escape");
                        }
                        i+=4;
                        break;
                        default:throw bad("escape");
                    }
                }
                b.append(c);
            }
            throw bad("unterminated string");
        }
    }
}

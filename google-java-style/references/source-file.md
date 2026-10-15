# 源文件基础与结构（Guide §2–3）

## 文件名与编码

- 含类的源文件名 = 唯一顶级类的类名 + `.java`（每个顶级类独占一个文件）。
- 编码一律 UTF-8。

## 特殊字符

- 除换行符外，源文件中唯一的空白字符是 ASCII 空格（0x20）。Tab 不用于缩进；其他空白字符在 char/字符串字面量和 text block 中必须转义。
- 有专用转义序列的字符（`\b` `\t` `\n` `\f` `\r` `\"` `\'` `\\`）一律用转义序列，不用八进制（`\012`）或 Unicode（`\u000a`）转义。
- 其余非 ASCII 字符：用真实 Unicode 字符（`∞`）或等价转义（`\u221e`）皆可，以哪个更易懂为准；字符串字面量和注释之外使用 Unicode 转义强烈不鼓励。

| 示例 | 评价 |
|------|------|
| `String unitAbbrev = "μs";` | 最佳：无需注释就清楚 |
| `String unitAbbrev = "\u03bcs"; // "μs"` | 允许，但没理由这么做 |
| `String unitAbbrev = "\u03bcs";` | 差：读者不知道是什么 |
| `return '\ufeff' + content; // byte order mark` | 好：不可打印字符用转义并加注释 |

不要因为「某些程序可能处理不好非 ASCII」而降低代码可读性——那种程序是坏的，应该修它。

## 文件结构

普通源文件按顺序由这些节组成（存在的节之间恰好一个空行）：

1. License/版权信息（如有）
2. package 声明（必填；不换行，不受列宽 100 限制；不使用 compact source files）
3. import
4. 恰好一个顶级类声明

`package-info.java` 同上但没有类声明；`module-info.java` 无 package 声明，类声明换成 module 声明。

## Import（§3.3）

- **禁止通配符导入**（static 或普通都不行）。
- **禁止 module import**：`import module java.base;` 不允许。
- **import 不换行**，不受列宽限制。
- 排序：所有 static import 一组，所有非 static import 一组；两组之间一个空行；组内不再有空行；组内按导入名字的 ASCII 排序（注意：是名字排序，不是 import 行排序——`.` 排在 `;` 前）。

```java
import static java.util.Arrays.asList;

import java.util.List;
import javax.example.Foo;
```

- **不对静态嵌套类使用 static import**，用普通 import 导入它们。

## 类声明（§3.4）

- 每个顶级类独占一个文件。
- 类成员与初始化器的顺序没有唯一正解，但必须采用**某个能向维护者解释清楚的逻辑顺序**；不要习惯性把新方法追加到类末尾——那是「按添加时间」排序，不是逻辑排序。
- **重载永不拆开**：同名方法（含多个构造器）必须连续放在一组，中间不插其他成员——即使它们之间 static/private 等修饰符不同。

## module-info（§3.5）

指令分块排序，每块之间一个空行：所有 `requires` 一块 → `exports` → `opens` → `uses` → `provides`。`requires` 上的修饰符顺序：`transitive static`。

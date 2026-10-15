---
name: google-java-style
description: 按 Google Java Style Guide 编写与审查 Java 代码：写新 Java 代码时直接套用其命名、格式、编程实践与 Javadoc 规则；审查/重构已有 Java 代码时按规范逐项检查并指出违反条款与改法；大段重排格式时建议官方 google-java-format。当用户要写 Java 代码、新建或修改 .java 文件、问「这段 Java 代码风格/规范有没有问题」、要求按 Google 风格检查或格式化 Java 代码，或在 Java 项目里生成代码时使用——即使用户没有明说「按规范写」。触发词：Google Java Style、Java 规范、Java 代码风格、Java 代码审查、Java 格式化、javaguide。
---

# Google Java Style

以 Google 官方 Java 编码标准（[javaguide](https://google.github.io/styleguide/javaguide.html)）为准绳写与审 Java 代码。本文件是核心规则，覆盖日常绝大多数场景；细则按需读 references/。

## 工作流

1. **写新 Java 代码**：直接套用下方「核心规则」与「标准文件骨架」。拿不准的具体构造（换行断点、switch、注解、text block）查 `references/formatting.md`。
2. **审查/重构已有代码**：按「审查清单」逐项过，指出「违反哪条 + 怎么改」；条款细节查对应 reference。
3. **大段代码需要重排格式**：建议先跑官方格式化工具 google-java-format（见文末），再人工核对它管不了的语义性规则（命名、@Override、异常处理、Javadoc 内容）。

## 按需读取

| 场景 | 文件 |
|------|------|
| import 顺序、文件结构、特殊字符、module 声明 | references/source-file.md |
| 大括号、缩进、列宽、换行断点、空格、switch/枚举/注解/注释/TODO/修饰符/text block | references/formatting.md |
| 命名与驼峰转换（缩写词、什么才算常量） | references/naming.md |
| @Override、异常处理、静态成员调用、finalizer | references/programming-practices.md |
| Javadoc 格式、summary 句式、何时必须写 | references/javadoc.md |

## 核心规则

### 命名

| 对象 | 规则 | 示例 |
|------|------|------|
| 包名 | 全小写连写，无下划线 | `com.example.deepspace` |
| 类名 | UpperCamelCase；测试类以 `Test` 结尾 | `ImmutableList`、`HashImplTest` |
| 方法名 | lowerCamelCase，动词开头；JUnit 测试方法可用下划线分段 | `sendMessage`、`transferMoney_deductsFromSource` |
| 常量 | UPPER_SNAKE_CASE，仅限**深度不可变**的 static final | `static final ImmutableList<String> NAMES` |
| 字段/参数/局部变量 | lowerCamelCase；局部 final 变量**不是**常量 | `computedValues` |
| 类型变量 | 单个大写字母可带数字，或类名形式 + `T` | `T`、`T2`、`RequestT` |

禁止前缀/后缀：`mName`、`s_name`、`name_` 都不合格。缩写词按整体小写再首字母大写：`XmlHttpRequest`、`newCustomerId`、`supportsIpv6OnIos`（完整算法见 references/naming.md）。

### 格式

- 缩进每级 **+2 空格**，只用空格不用 Tab；换行续行至少 **+4**。
- 列宽 **100 字符**（package 行、import 行、text block 内容等例外）。
- 大括号 K&R（`{` 不换行、`}` 独占一行）；`if/else/for/do/while` 即使空体或单语句也**必须**带大括号。
- 一行一条语句。
- import：**禁通配符**；static 一组在前、非 static 一组在后，组间一个空行，组内 ASCII 排序，不换行。
- 类的连续成员之间一个空行（两个连续字段之间的空行可选，用于逻辑分组）。
- 修饰符按 JLS 顺序：`public protected private abstract default static final sealed non-sealed transient volatile synchronized native strictfp`。
- long 字面量用大写 `L`：`3000000000L`。
- 数组方括号写在类型上：`String[] args`，不是 `String args[]`；一次只声明一个变量（for 头除外）；局部变量就近声明。

### 编程实践

- `@Override` 能加必加（父方法本身是 `@Deprecated` 时可省）。
- 捕获的异常不许静默吞掉；确实无需处理时用注释说明理由。
- 静态成员用类名限定：`Foo.aStaticMethod()`，不是 `aFoo.aStaticMethod()`。
- 不重写 `Object.finalize`。
- 每个 switch 都必须穷尽（语言不要求时也要，必要时加空 `default`）；旧式 switch 的 fall-through 必须加注释（`// fall through`）。
- 可见的 public 类与 public/protected 成员至少要有 Javadoc，summary 是名词/动词短语，不写 "This method returns ..."。

## 标准文件骨架

各节之间恰好一个空行；static import 与非 static import 分组：

```java
// Copyright 2026 Example Inc.（如有才写，与 package 之间空一行）

package com.example.order;

import static java.util.Objects.requireNonNull;

import java.time.Instant;
import java.util.List;

/** Parses raw order text into an immutable, line-indexed view. */
public final class OrderParser {

  private static final int MAX_LINE_COUNT = 100;

  private final List<String> lines;
  private final Instant parsedAt;

  public OrderParser(List<String> lines) {
    this.lines = List.copyOf(requireNonNull(lines));
    this.parsedAt = Instant.now();
  }

  public boolean exceedsLineLimit() {
    return lines.size() > MAX_LINE_COUNT;
  }

  @Override
  public String toString() {
    return "OrderParser{lineCount=" + lines.size() + "}";
  }
}
```

## 审查清单

1. **文件结构**（references/source-file.md）：UTF-8；文件名 = 唯一顶级类名；license → package → import → 类，各节间恰好一个空行；无通配符与 `import module`；import 两组排序正确；不对静态嵌套类 static import；重载方法不拆开。
2. **格式**（references/formatting.md）：缩进 2/续行 4+；列宽 100；K&R 与必带大括号；一行一句；空行与水平空格；换行断点方向（非赋值运算符前断、赋值运算符后断）；修饰符顺序；枚举/数组/switch/注解/注释/TODO/text block 各构造细则。
3. **命名**（references/naming.md）：各类标识符大小写；可变对象误用 UPPER_SNAKE_CASE；局部 final 变量按常量风格写；驼峰转换（缩写词）。
4. **编程实践**（references/programming-practices.md）：@Override 缺失；吞异常；静态成员用实例限定；finalize；switch 不穷尽；fall-through 无注释。
5. **Javadoc**（references/javadoc.md）：可见成员缺失文档；summary 写成完整句子或 "This method returns ..."；block tag 顺序（`@param` `@return` `@throws` `@deprecated`）与空描述。

## 自动格式化

google-java-format 是这份规范的参考实现（规范中明确：某些场景以它的输出为准）。用户想自动重排格式时：`google-java-format --replace <files>`。注意它只管格式——命名、@Override、异常处理、Javadoc 内容仍需按上面清单人工审。

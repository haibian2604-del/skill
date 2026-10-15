# 格式（Guide §4）

术语：block-like construct 指类、方法、构造器或 switch 的体。数组初始化器可任选当作 block-like construct 处理。

## 大括号

- `if` `else` `for` `do` `while` 即使体为空或只有一条语句，也必须加大括号。lambda 等其他可选大括号保持可选。
- 非空块用 K&R 风格：`{` 前不换行；`{` 后换行；`}` 前换行；`}` 后仅当它终止语句或方法/构造器/具名类的体时才换行（后跟 `else` 或逗号时不换）。
- 空块可以写成 `{}`，也可以 K&R；但**多块语句**（if/else、try/catch/finally 中直接包含多个块）里不允许紧凑空块：

```java
// 可接受
void doNothing() {}

// 不可接受：多块语句里不许紧凑空块
try {
  doSomething();
} catch (Exception e) {}
```

## 缩进与语句

- 每开一个新块缩进 +2 空格（代码和注释都适用）；只用空格，不用 Tab。
- 每条语句后换行。

## 列宽：100

任何超限的行必须换行，无例外情形见下。例外：不可能遵守的行（如 Javadoc 里的长 URL）；package 和 import；text block 内容；注释里可复制到 shell 的命令行；极长的标识符（此时周边代码按 google-java-format 的输出换行）。全角字符等宽度过大的 Unicode 码点按一个字符计，可自行提前换行。

## 换行

没有唯一公式；主 directive：**优先在更高的语法层级断行**。提取方法/局部变量常常比换行更好。

1. 在**非赋值**运算符处断行时，断在符号**之前**（与 C++/JavaScript 的 Google 风格相反）。这同样适用于：点分隔符 `.`、方法引用 `::`、类型边界 `&`（`<T extends Foo & Bar>`）、catch 的 `|`。
2. 在**赋值**运算符处断行时，通常断在符号**之后**（断在前也可）。foreach 的 `:` 同此。
3. 方法/构造器/record 类名与其后的 `(` 不分开。
4. 逗号与它前面的 token 不分开。
5. lambda/switch 规则的箭头旁不断行——例外：箭头后是不加大括号的单个表达式时，可在箭头后断。

```java
MyLambda<String, Long, Object> lambda =
    (String label, Long value, Object obj) -> {
      ...
    };

Predicate<String> predicate = str ->
    longExpressionInvolving(str);
```

- 续行相对首行缩进**至少 +4**；多条续行中，语法上平行的行用同一缩进。
- 换行的首要目标是清晰，不是最少行数。

## 空白

### 垂直空行

- 类的连续成员/初始化器（字段、构造器、方法、嵌套类、静态/实例初始化器）之间**必有一个空行**。例外：两个连续字段之间的空行可选，用于字段逻辑分组；枚举常量之间见枚举节。
- 其他规则要求处（文件结构各节之间、import 两组之间）。
- 任何提高可读性处可加单个空行；类首成员前/末成员后的空行不鼓励也不禁止；多个连续空行允许但从不要求。

### 水平空格

除语言要求外，仅以下位置出现单个 ASCII 空格：

1. `if` `for` `catch` 等保留字与其后的 `(`
2. `else` `catch` 等保留字与其前的 `}`
3. 任何 `{` 之前（例外：`@SomeAnnotation({a, b})`；`String[][] x = {{"foo"}};` 的 `{{` 之间不要求）
4. 任何二元/三元运算符两侧，包括类型边界 `&`、catch `|`、foreach `:`、lambda/switch 箭头；**不包括**方法引用 `::` 和点 `.`
5. `,:;` 之后、cast 的 `)` 之后
6. `//` 注释与前面的内容之间（可多空格）
7. `//` 与注释文字之间（可多空格）
8. 声明中类型与标识符之间：`List<String> list`
9. 数组初始化器大括号内侧（可选）：`new int[] {5, 6}` 与 `new int[] { 5, 6 }` 皆可
10. 类型注解与 `[]` 或 `...` 之间

### 水平对齐

为对齐 token 而加可变数量空格的做法允许但**从不要求**，也不要求维持既有对齐。为对齐而改动本来不受影响的行会污染版本历史、拖慢 review、加剧冲突——这些考虑优先于对齐。

```java
private int x; // this is fine
private Color color; // this too

private int   x;      // permitted, but future edits
private Color color;  // may leave it unaligned
```

## 分组括号

可选的分组括号仅在「作者和审查者都认为不加也不会被误读、加了也不会更易读」时才省略。不要假设读者背得出整个运算符优先级表。

## 具体构造

### 枚举

枚举常量后的逗号后可换行（可再加空行）。无方法且常量无文档的枚举可写成数组初始化器式：

```java
private enum Suit { CLUBS, HEARTS, SPADES, DIAMONDS }
```

其余类规则全部适用于枚举。

### 变量声明

- 一次只声明一个变量：`int a, b;` 不用（for 循环头例外）。
- 局部变量在首次使用点附近声明（不习惯性堆在块开头），通常带初始化器或声明后立即初始化。

### 数组

- 初始化器可按块状格式化（多种写法都合法）。
- 方括号属于类型：`String[] args`，不是 `String args[]`。

### switch

- 缩进：switch 块内容 +2，每个 switch label 从 +2 处开始。新式规则若不超列宽可写成单行；带非空块时 `{` 后必须换行，块内再 +2。旧式的冒号后换行，语句组内再 +2。

```java
switch (number) {
  case 0, 1 -> handleZeroOrOne();
  case 2 ->
      handleTwoWithAnExtremelyLongMethodCallThatWouldNotFitOnTheSameLine();
  default -> {
    logger.atInfo().log("Surprising number %s", number);
    handleSurprisingNumber(number);
  }
}
```

- **fall-through 必须注释**（旧式）：每个语句组要么以 break/continue/return/抛异常终止，要么用注释标明会（可能）落入下一组（通常写 `// fall through`）；最后一个语句组不需要。新式 switch 无 fall-through。

```java
switch (input) {
  case 1:
  case 2:
    prepareOneOrTwo();
  // fall through
  case 3:
    handleOneTwoOrThree();
    break;
  default:
    handleLargeNumber(input);
}
```

- **穷尽性**：Google Style 要求**每一个** switch 都穷尽（语言本身不要求时也要），必要时加空的 `default`。
- **switch 表达式必须用新式（箭头）**。

### 注解

- type-use 注解（被 `@Target(ElementType.TYPE_USE)` 元注解的）紧贴在所注类型之前：`final @Nullable String name;`
- 类/package/module/方法/构造器上的注解在文档块之后，每个注解独占一行（这不算换行，不增加缩进）。例外：方法/构造器只有单个无参注解时，可与签名首行同行：`@Override public int hashCode() { ... }`
- 字段注解也在文档块之后，但多个注解可同行：`@Partial @Mock DataLoader loader;`
- 参数与局部变量的注解无特定规则（type-use 除外）。

### 注释与 TODO

- 块注释与周围代码同缩进，`/* ... */` 或 `// ...` 皆可；多行 `/* ... */` 的后续行以与上行对齐的 `*` 开头。注释不用星号画框。想让格式化工具自动重排段落就用 `/* ... */`。
- TODO 用于临时方案/短期方案/够用但不完美之物。格式：全大写 `TODO` + 冒号 + 指向上下文的链接（最好是 bug 引用）+ 连字符 + 说明：

```java
// TODO: crbug.com/12345678 - Remove this after the 2047q4 compatibility window expires.
```

避免以个人/团队为上下文的 TODO。带日期的 TODO 要写具体日期或具体事件。

### 修饰符

类与成员修饰符按 JLS 推荐顺序：

```
public protected private abstract default static final sealed non-sealed
  transient volatile synchronized native strictfp
```

### 数字字面量

long 用大写 `L`：`3000000000L`，不用小写 `l`（避免与 1 混淆）。

### Text block

开 `"""` 独占一行；闭 `"""` 与开的对齐独占一行（其后可跟代码）；文本块每行缩进至少与 `"""` 相同。内容可超列宽。

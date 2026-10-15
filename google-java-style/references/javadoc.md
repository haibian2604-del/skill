# Javadoc（Guide §7）

## 格式

Markdown Javadoc（`///`）与传统 Javadoc（`/** */`）都可接受：

```java
/// Javadoc text is written here,
/// wrapped normally...
public int method(String p1) { ... }
```

```java
/**
 * Multiple lines of Javadoc text are written here,
 * wrapped normally...
 */
public int method(String p1) { ... }
```

基本形式永远可用；整个块（含注释标记）能放一行且**没有块标签**（如 `@param`）时可用单行形式：`/** An especially short bit of Javadoc. */`

**段落**：传统式段落间用只含对齐 `*` 的空行，且在块标签组前也空一行；第一段之后的每段首词前紧跟 `<p>`（无空格）；`<ul>` `<table>` 等其他块级元素前不加 `<p>`。Markdown 式按 Markdown 惯例用空行分段，不需要 `<p>`。

**块标签**：出现的标准块标签按 `@param`、`@return`、`@throws`、`@deprecated` 排序，且描述都不许为空。放不下一行时续行缩进：传统式从 `@` 位置起 4+ 空格；Markdown 式恰好 2 空格（4 空格在某些语境会被当缩进代码块）。

## Summary fragment

每个 Javadoc 块以简短 summary fragment 开头——它是类/方法索引里唯一显示的部分。它是**名词短语或动词短语，不是完整句子**：不以 "`A `Foo` is a...`"、"`This method returns...`" 开头，也不是 "Save the record." 这样的完整祈使句；但首字母大写并按完整句子加标点。

`/// @return the customer ID` 是常见错误，应改成 `/// Returns the customer ID.` 或 `/// {@return the customer ID}`。

## 何时必须有

至少为每个**可见**的类、成员、record 组件写 Javadoc：顶级类 public 即可见；成员 public/protected 且所在类可见即可见；record 组件在其 record 可见时可见。

例外：

1. **自解释成员**：`getFoo()` 这类「简单、显然」的成员，且**真没有**其他值得说的，可省。但不能拿这条当借口省略读者可能需要的信息（如 `canonicalName` 组件，若读者可能不懂 "canonical name" 是什么，就别省）。
2. **覆盖方法**：覆盖父类型方法的方法不一定有。

其他类/成员按需要写。凡是要用实现注释说明类/成员的整体用途或行为时，改写成 Javadoc（`///` 或 `/**`）。非必需的 Javadoc 不强制遵守上述格式细则，但推荐遵守。

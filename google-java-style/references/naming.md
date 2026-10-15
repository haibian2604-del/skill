# 命名（Guide §5）

## 通用规则

- 标识符只用 ASCII 字母和数字（下划线仅限下文少数场景），即 `\w+`。
- **不用特殊前缀/后缀**：`name_`、`mName`、`s_name`、`kName` 都不是 Google 风格。

## 各类标识符

| 对象 | 规则 | 示例 |
|------|------|------|
| 包名/module 名 | 仅小写字母和数字，无下划线，单词直接连写 | `com.example.deepspace`（不是 `deepSpace`、`deep_space`） |
| 类名 | UpperCamelCase，名词或名词短语；接口也可是形容词（`Readable`） | `Character`、`ImmutableList`、`List` |
| 测试类 | 以 `Test` 结尾；覆盖单个类时 = 类名 + `Test` | `HashIntegrationTest`、`HashImplTest` |
| 方法名 | lowerCamelCase，动词或动词短语 | `sendMessage`、`stop` |
| JUnit 测试方法 | 可用下划线分隔逻辑组件，每段 lowerCamelCase | `transferMoney_deductsFromSource` |
| 常量 | UPPER_SNAKE_CASE | `NUMBER`、`NAMES` |
| 非常量字段 | lowerCamelCase，名词/名词短语 | `computedValues`、`index` |
| 参数 | lowerCamelCase；公共方法避免单字符名 | |
| 局部变量 | lowerCamelCase；即使是 final 且不可变的局部变量也**不算常量**，不按常量风格写 | |
| 类型变量 | 单个大写字母可后跟单个数字（`E` `T` `X` `T2`），或类名形式 + `T`（`RequestT`、`FooBarT`） | |
| 未命名变量 | 适用处允许 `_` | `Predicate<String> alwaysTrue = _ -> true;` |

## 什么才算「常量」

常量 = static final 且**内容深度不可变**、其方法无可检测副作用。原始类型、字符串、不可变值类、置为 null 的都算；只要可观察状态能变就不算——「打算不改」不够。

```java
// 常量
static final int NUMBER = 5;
static final ImmutableList<String> NAMES = ImmutableList.of("Ed", "Ann");
static final Joiner COMMA_JOINER = Joiner.on(','); // Joiner 不可变
static final SomeMutableType[] EMPTY_ARRAY = {};

// 不是常量
static String nonFinal = "non-final";
final String nonStatic = "non-static";
static final Set<String> mutableCollection = new HashSet<>();
static final ImmutableSet<SomeMutableType> mutableElements = ImmutableSet.of(mutable);
static final Logger logger = Logger.getLogger(...); // Logger 可变
static final String[] nonEmptyArray = {"these", "can", "change"};
```

## 驼峰转换

从英文短语到标识符的（近乎）确定性算法：

1. 转纯 ASCII、去撇号（"Müller's algorithm" → "Muellers algorithm"）。
2. 按空格和剩余标点（通常连字符）切词；推荐把已有驼峰外观的常见词拆开（"AdWords" → "ad words"）；"iOS" 这类无法归约的词不适用此推荐。
3. 全部转小写（含缩写词），然后仅把每词首字母大写（upper camel）或除第一词外大写（lower camel）。
4. 拼接。极少数情况（多段版本号）可用下划线分隔相邻数字。

| 短语 | 正确 | 错误 |
|------|------|------|
| "XML HTTP request" | `XmlHttpRequest` | `XMLHTTPRequest` |
| "new customer ID" | `newCustomerId` | `newCustomerID` |
| "inner stopwatch" | `innerStopwatch` | `innerStopWatch` |
| "supports IPv6 on iOS?" | `supportsIpv6OnIos` | `supportsIPv6OnIOS` |
| "YouTube importer" | `YouTubeImporter`、`YoutubeImporter`（后者不推荐） | |
| "Turn on 2SV" | `turnOn2sv` | `turnOn2Sv` |
| "Guava 33.4.6" | `guava33_4_6` | `guava3346` |

注：英文里 "nonempty"/"non-empty" 都对，所以 `checkNonempty` 与 `checkNonEmpty` 都正确。

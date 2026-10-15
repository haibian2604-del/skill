# 编程实践（Guide §6）

## @Override：能加必加

方法只要在合法覆盖的位置就必须标 `@Override`：覆盖父类方法、实现接口方法、接口方法重新声明父接口方法、record 组件显式声明的访问器。例外：父方法本身是 `@Deprecated` 时可省略。

## 捕获的异常：不许忽略

对捕获的异常什么都不做几乎总是错的（典型做法：记日志；若认为「不可能发生」，重新抛为 `AssertionError`）。确实什么都不做才正确时，在 catch 块里用注释说明为什么：

```java
try {
  int i = Integer.parseInt(response);
  return handleNumericResponse(i);
} catch (NumberFormatException _) {
  // it's not numeric; that's fine, just continue
}
return handleTextResponse(response);
```

## 静态成员：用类名限定

必须限定静态成员时用类名，不用该类型的引用/表达式：

```java
Foo aFoo = ...;
Foo.aStaticMethod(); // good
aFoo.aStaticMethod(); // bad
somethingThatYieldsAFoo().aStaticMethod(); // very bad
```

## Finalizer：不用

不要重写 `Object.finalize`——finalization 已计划移除。

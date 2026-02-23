from web.context_injector import ContextBuilder

print("Testing build_cpu_memory_context()...")
result = ContextBuilder.build_cpu_memory_context()
print(f"Result length: {len(result)}")
print("---")
print(result if result else "[EMPTY]")
print("---")

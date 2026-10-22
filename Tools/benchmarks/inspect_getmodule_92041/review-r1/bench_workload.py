import sys
frame = sys._getframe()
try: 1/0
except ZeroDivisionError as e: tb = e.__traceback__
def stack(n, context):
    if n: return stack(n-1, context)
    return inspect.stack(context=context)
def function(): pass

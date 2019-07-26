class Foo(object):
    def foo(x, y):
        print(x)
        self.x = y
        x = self.x
    
    t = 5

def main():
    foo = Foo()
    foo.foo(1, 3)

if __name__ == '__main__':
    main()

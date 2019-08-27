project('pex-loader', 'cpp', version: '0.0.0', default_options: ['cpp_std=c++17'])


sources = [
    'src/read_early_header.cpp',
]

includes = include_directories(
    'include',
)


test_sources = ['test/src/test.cpp']
test_includes = [include_directories('test/include')] + [includes]


libpex_loader = library(
    'pex_loader',
    sources,
    include_directories: includes,
)


catch2_test_executable = executable(
    'catch2_test',
    test_sources,
    include_directories: test_includes,
    link_with: libpex_loader,
)

test('catch2_test_suit', catch2_test_executable)

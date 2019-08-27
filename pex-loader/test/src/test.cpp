#define CATCH_CONFIG_MAIN
#include <catch.hpp>

#include <pex_loader/pex_loader.hpp>
#include <pex_loader/read_uint.hpp>

#include <string_view>


using namespace std::literals;
using Catch::Matchers::Predicate;


TEST_CASE("read_uint is working", "[read_uint]") {
    using pex::uint::read_uint;
    CHECK((read_uint<uint32_t>("\x74\x91\xb2\x03"sv) == 1955705347u));
    CHECK((read_uint<uint8_t>("\x74\x91\xb2\x03"sv) == 0x74u));
    CHECK((read_uint<uint8_t>("\x94\x91\xb2\x03"sv) == 0x94u));
    CHECK((read_uint<uint32_t>("\x00\x00\x00\x00"sv) == 0));
    CHECK((read_uint<uint32_t>("\x00\x00\x00\x00\x12"sv) == 0));
    REQUIRE_THROWS_AS((read_uint<uint64_t, true>("\x00\x00\x00\x00\x12\x14\x63"sv)), std::logic_error);
    REQUIRE_NOTHROW((read_uint<uint64_t, true>("\x00\x00\x00\x00\x12\x14\x63\x1e"sv)));
}

TEST_CASE("read_early_header is working", "[read_early_header]") {
    using namespace pex::loader;

    auto info = read_early_header("PEX\x01\x00\x00\x00\x00"sv);
    CHECK(info.file_type == EarlyHeaderInfo::FileType::executable);
    CHECK((info.format_version.major == 0u && info.format_version.minor == 0u));

    info = read_early_header("PEX\x00\x12\x34\x56\x78TRASH,JUNK,GARBAGE"sv);
    CHECK(info.file_type == EarlyHeaderInfo::FileType::other);
    CHECK((info.format_version.major == 0x1234u && info.format_version.minor == 0x5678u));

    info = read_early_header("PEX\x02\x00\x00\x00\x01"sv);
    CHECK(info.file_type == EarlyHeaderInfo::FileType::library);
    CHECK((info.format_version.major == 0x0u && info.format_version.minor == 0x1u));

    CHECK_THROWS_MATCHES(
        read_early_header("PEX\x74\x00\x00\x00\x00"sv),
        LoaderError,
        Predicate<LoaderError>([](const LoaderError& e) {
            return std::string_view(e.what()).find("Invalid or unsupported file type") != std::string_view::npos;
        })
    );

    CHECK_THROWS_MATCHES(
        read_early_header("PeX\x01\x00\x00\x00\x00"sv),
        LoaderError,
        Predicate<LoaderError>([](const LoaderError& e) {
            return std::string_view(e.what()).find("Invalid file magic") != std::string_view::npos;
        })
    );

    CHECK_THROWS_MATCHES(
        read_early_header("PEX\x01\x00\x00\x00"sv),
        LoaderError,
        Predicate<LoaderError>([](const LoaderError& e) {
            return std::string_view(e.what()).find("Unexpected EOF") != std::string_view::npos;
        })
    );
}

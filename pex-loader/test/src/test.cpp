#define CATCH_CONFIG_MAIN
#define CATCH_CONFIG_FAST_COMPILE
#include <catch.hpp>

#include <pex_loader/data_reader.hpp>
#include <pex_loader/pex_loader.hpp>
#include <pex_loader/read_uint.hpp>

#include <list>
#include <string_view>
#include <vector>


using namespace std::literals;
using Catch::Matchers::Predicate;


TEST_CASE("read_uint is working", "[read_uint]") {
    using pex::util::read_uint;
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

TEST_CASE("DataReader::read_bytes is working", "[DataReader]") {
    using namespace pex::loader;
    using namespace pex::util;
    {
        DataReader r(""sv);
        uint8_t buf[1];
        REQUIRE_NOTHROW(
            r.read_bytes(0, buf)
        );
        REQUIRE_THROWS_AS(
            r.read_bytes(1, buf),
            DataReader::EofError
        );
    }
    {
        DataReader r("Python is cool"sv);
        
        SECTION("Exact number of bytes is written") {
            std::string buf = "01234567890123456789";
            r.read_bytes(7, buf.begin());
            REQUIRE(buf == "Python 7890123456789");
        }
        SECTION("Different iterator types work") {
            SECTION("std::string iterator works") {
                std::string buf = "abcdef";
                r.read_bytes(6, buf.begin());
                REQUIRE(buf == "Python");
            }
            SECTION("std::vector iterator works") {
                std::vector<char> buf(6);
                r.read_bytes(6, buf.begin());
                REQUIRE((buf == std::vector<char>{'P', 'y', 't', 'h', 'o', 'n'}));
            }
            SECTION("std::list<uint8_t> iterator works") {
                std::list<uint8_t> buf = {0, 0, 0, 0, 0, 0};
                r.read_bytes(6, buf.begin());
                REQUIRE((buf == std::list<uint8_t>{'P', 'y', 't', 'h', 'o', 'n'}));
            }
            SECTION("char* works") {
                char buf[6] = {0, 0, 0, 0, 0, 0};
                r.read_bytes(6, buf);
                REQUIRE(std::string_view(buf, 6) == "Python");
            }
        }
        SECTION("Sequential reads work") {
            std::string buf = "01234567890123456789";
            r.read_bytes(7, buf.begin());
            REQUIRE(buf == "Python 7890123456789");
            r.read_bytes(3, buf.begin());
            REQUIRE(buf == "is hon 7890123456789");
            r.read_bytes(3, buf.begin());
            REQUIRE(buf == "coohon 7890123456789");
            REQUIRE_THROWS_AS(r.read_bytes(2, buf.begin()), DataReader::EofError);
            r.read_bytes(1, buf.begin());
            REQUIRE(buf == "loohon 7890123456789");
        }
    }
}

TEST_CASE("DataReader::skip is working", "[DataReader]") {
    using namespace pex::loader;
    using namespace pex::util;
    DataReader r("Python is cool"sv);
    std::string buf = "01234567890123456789";
    r.skip(4);
    r.read_bytes(6, buf.begin());
    REQUIRE(buf == "on is 67890123456789");
    REQUIRE_THROWS_AS(r.skip(5), DataReader::EofError);
    r.skip(4);
    REQUIRE_THROWS_AS(r.read_bytes(1, buf.begin()), DataReader::EofError);
    REQUIRE_NOTHROW(r.skip(0));
    REQUIRE_THROWS_AS(r.skip(1), DataReader::EofError);
}

TEST_CASE("DataReader::get_{offset,number_of_bytes_left} are working", "[DataReader]") {
    using namespace pex::loader;
    using namespace pex::util;
    DataReader r("Python is cool"sv);
    CHECK(r.get_offset() == 0);
    CHECK(r.get_number_of_bytes_left() == 14);

    std::string buf = "01234567890123456789";
    r.skip(4);
    CHECK(r.get_offset() == 4);
    CHECK(r.get_number_of_bytes_left() == 10);
    r.read_bytes(6, buf.begin());
    CHECK(r.get_offset() == 10);
    CHECK(r.get_number_of_bytes_left() == 4);
    r.skip(4);
    CHECK(r.get_offset() == 14);
    CHECK(r.get_number_of_bytes_left() == 0);
}

TEST_CASE("DataReader::read_uint is working", "[DataReader]") {
    using namespace pex::loader;
    using namespace pex::util;
    DataReader r("\x12\x34\x56\x78\x9A\xBC\xDE\xF0"sv);

    SECTION("8 bytes = 2 * uint32_t") {
        CHECK(r.read_uint<uint32_t>() == 0x1234'5678u);
        CHECK(r.read_uint<uint32_t>() == 0x9ABC'DEF0u);
        REQUIRE_THROWS_AS(r.read_uint<uint8_t>(), DataReader::EofError);
    }
    SECTION("8 bytes = 1 * uint64_t") {
        CHECK(r.read_uint<uint64_t>() == 0x1234'5678'9ABC'DEF0ULL);
        REQUIRE_THROWS_AS(r.read_uint<uint8_t>(), DataReader::EofError);
    }
    SECTION("8 bytes = uint32_t + uint8_t + NOT uint32_t") {
        CHECK(r.read_uint<uint32_t>() == 0x1234'5678u);
        CHECK(r.read_uint<uint8_t>() == 0x9Au);
        REQUIRE_THROWS_AS(r.read_uint<uint32_t>(), DataReader::EofError);
    }
}

TEST_CASE("v0::read_sections is working", "[read_sections]") {
    using namespace pex::loader;
    SECTION("0 sections") {
        auto blob = (
            "\x00\x00\x00\x00\x00\x00\x00\x00"
            ""sv
        );
        CHECK(v0::read_sections(blob).size() == 0);
    }
    SECTION("invalid section number") {
        auto blob = (
            "\x00\x00\x00\x00\x00\x00\x00"
            ""sv
        );
        REQUIRE_THROWS(v0::read_sections(blob));
    }
    SECTION("3 sections, valid") {
        auto blob = (
            "\x00\x00\x00\x00\x00\x00\x00\x03"
            
            // Section 0
            // Size: 5 + 4 = 9
            "\x00\x00\x00\x00\x00\x00\x00\x09"
            // Name: 1234
            "1234"
            // Offset: 8 + 8 + 4 = 20
            // Data
            "Hello"

            // Section 1
            // Size: 0 + 4 = 4
            "\x00\x00\x00\x00\x00\x00\x00\x04"
            // Name: test
            "test"
            // Offset: (20 + 5) + 8 + 4 = 37
            // Zero-length data

            // Section 2
            // Size: 16 + 4 = 30
            "\x00\x00\x00\x00\x00\x00\x00\x14"
            // Name "\x00\x01\x02\x03"
            "\x00\x01\x02\x03"
            // Offset: (37 + 0) + 8 + 4 = 49
            // Data
            "0123456789abcdef"

            ""sv
        );

        auto sections = v0::read_sections(blob);
        REQUIRE(sections.size() == 3);
        CHECK(sections[0].name == std::array<char, 4>{'1', '2', '3', '4'});
        CHECK(sections[0].size == 5);
        CHECK(sections[0].offset == 20);

        CHECK(sections[1].name == std::array<char, 4>{'t', 'e', 's', 't'});
        CHECK(sections[1].size == 0);
        CHECK(sections[1].offset == 37);

        CHECK(sections[2].name == std::array<char, 4>{0, 1, 2, 3});
        CHECK(sections[2].size == 16);
        CHECK(sections[2].offset == 49);
    }
    SECTION("3 sections, EOF in data") {
        auto blob = (
            "\x00\x00\x00\x00\x00\x00\x00\x03"
            
            // Section 0
            // Size: 5
            "\x00\x00\x00\x00\x00\x00\x00\x05"
            // Name: 1234
            "1234"
            // Offset: 8 + 8 + 4 = 20
            // Data
            "Hello"

            // Section 1
            // Size: 0
            "\x00\x00\x00\x00\x00\x00\x00\x00"
            // Name: test
            "test"
            // Offset: (20 + 5) + 8 + 4 = 37
            // Zero-length data

            // Section 2
            // Size: 16
            "\x00\x00\x00\x00\x00\x00\x00\x10"
            // Name "\x00\x01\x02\x03"
            "\x01\x02\x03\x04"
            // Offset: (37 + 0) + 8 + 4 = 59
            // Data
            "0123456789abcde"   // Oops... 1 byte is missing

            ""sv
        );

        REQUIRE_THROWS(v0::read_sections(blob));
    }
    SECTION("3 sections, 1 absent") {
        auto blob = (
            "\x00\x00\x00\x00\x00\x00\x00\x03"
            
            // Section 0
            // Size: 5
            "\x00\x00\x00\x00\x00\x00\x00\x05"
            // Name: 1234
            "1234"
            // Offset: 8 + 8 + 4 = 20
            // Data
            "Hello"

            // Section 1
            // Size: 0
            "\x00\x00\x00\x00\x00\x00\x00\x00"
            // Name: test
            "test"
            // Offset: (20 + 5) + 8 + 4 = 37
            // Zero-length data

            // A section is missing

            ""sv
        );

        REQUIRE_THROWS(v0::read_sections(blob));
    }
}

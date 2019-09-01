#pragma once

#include <pex_loader/read_uint.hpp>

#include <array>
#include <cstdint>
#include <exception>
#include <string>
#include <string_view>
#include <vector>


/// Top-level namespace for pex-loader functions and classes
namespace pex::loader
{

/// An exception thrown when the PEX file cannot be loaded
class LoaderError : public std::runtime_error
{
public:
    LoaderError(const std::string& message):
        std::runtime_error(message)
    { }
};


/// Contains information encoded in the early header
struct EarlyHeaderInfo
{
    enum class FileType
    {
        other = 0,
        executable = 1,
        library = 2,
    };

    struct FormatVersion
    {
        uint16_t major;
        uint16_t minor;
    };

    FileType file_type;
    FormatVersion format_version;
};

EarlyHeaderInfo read_early_header(const std::string_view& data);


/// Format major version 0
namespace v0
{
    /// Section in PEX file
    struct Section
    {
        uint64_t offset;
        uint64_t size;
        std::array<char, 4> name;
    };

    std::vector<Section> read_sections(const std::string_view& data);
}


} // namespace pex::loader

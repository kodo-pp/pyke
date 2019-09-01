#include <pex_loader/pex_loader.hpp>
#include <pex_loader/read_uint.hpp>


namespace pex::loader
{

EarlyHeaderInfo read_early_header(const std::string_view& data)
{
    if (data.length() < 8) {
        throw LoaderError("Unexpected EOF while reading early header");
    }
    EarlyHeaderInfo info;

    // Check magic signature
    auto magic = data.substr(0, 3);
    if (magic != "PEX") {
        throw LoaderError("Invalid file magic signature");
    }

    // Determine the file type
    auto encoded_file_type = uint8_t(data[3]);
    switch (encoded_file_type) {
        case 0: {
            info.file_type = EarlyHeaderInfo::FileType::other;
            break;
        }
        case 1: {
            info.file_type = EarlyHeaderInfo::FileType::executable;
            break;
        }
        case 2: {
            info.file_type = EarlyHeaderInfo::FileType::library;
            break;
        }
        default: {
            throw LoaderError(
                "Invalid or unsupported file type: "
                + std::to_string(static_cast<unsigned int>(encoded_file_type))
            );
        }
    }

    // Determine the format version
    auto encoded_format_version = pex::util::read_uint<uint32_t>(data.substr(4));
    auto format_major_version = uint16_t((encoded_format_version >> 16) & 0xFFFFu);
    auto format_minor_version = uint16_t(encoded_format_version & 0xFFFFu);
    info.format_version = EarlyHeaderInfo::FormatVersion{format_major_version, format_minor_version};

    return info;
}

}

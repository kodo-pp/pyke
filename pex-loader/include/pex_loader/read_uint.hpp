#pragma once

#include <type_traits>
#include <stdexcept>


namespace pex::util
{

/// Read fixed-size unsigned int encoded in big endian
///
/// @param Uint: unsigned integer type to read. Its size (in bytes) is the
/// number of bytes read from `data`. Must be an unsigned integer
///
/// @param do_check: whether to check the actual number of bytes available
/// in `data` or not. Default to false for the sake of performance
///
/// @param data: the buffer to read from
///
/// @throws std::logic_error with the appropriate message if `do_check` is
/// true and `data.length() < sizeof(Uint)`
///
/// @returns the unsigned integer formed by the read bytes (big endian)
template <typename Uint, bool do_check = false>
Uint read_uint(const std::string_view& data)
{
    static_assert(std::is_integral_v<Uint>);
    static_assert(std::is_unsigned_v<Uint>);

    if constexpr (do_check) {
        if (data.length() < sizeof(Uint)) {
            throw std::logic_error("read_uint: the buffer is smaller than the size of integer read from it");
        }
    }

    Uint result = 0;
    for (size_t i = 0; i < sizeof(Uint); ++i) {
        uint8_t byte = data[i];
        result <<= 8;
        result |= Uint(byte);
    }
    return result;
}

} // namespace pex::util

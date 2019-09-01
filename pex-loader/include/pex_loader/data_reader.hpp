#pragma once

#include <pex_loader/read_uint.hpp>

#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>


namespace pex::util
{

/// Utility class to make binary sequential data reading easier
///
/// Thread safety: not thread safe. You may need to use locking yourself
/// if you are using an object of this class from multiple threads concurrently
class DataReader
{
public:
    /// Exception representing premature end-of-file condition
    class EofError : public std::runtime_error
    {
    public:
        EofError(const std::string& message);
    };

    explicit DataReader(std::string_view data) noexcept:
        data(std::move(data))
    { }

    /// Get the current offset in bytes (== number of already read bytes)
    size_t get_offset() const noexcept;

    /// Get the size of the remaining (that haven't yet been read) data in bytes
    size_t get_number_of_bytes_left() const noexcept;

    /// Skip the specified number of bytes (mark them as read, but don't do anything with them)
    /// @param length - number of bytes to skip
    ///
    /// @throws EofError if there is ledd bytes left than is requested to skip
    ///
    /// Exception safety: strong guarantee: if an exception is thrown, DataReader object is unchanged
    void skip(size_t length);

    /// Read (big-endian) unsigned integer of given size
    /// @throws DataReader::EofError if there is not enough data
    ///
    /// Exception safety: strong guarantee: if an exception is thrown, DataReader object is unchanged
    template <typename Uint>
    Uint read_uint()
    {
        // pex::util::read_uint already ensures that Uint is a valid type
        // We only need to make sure there is enough data to read sizeof(Uint) bytes
        const auto int_size = sizeof(Uint);
        if (get_number_of_bytes_left() < int_size) {
            const auto number_of_bits = int_size * 8;
            throw EofError("not enough data to read " + std::to_string(number_of_bits) + "-bit integer");
        }

        auto value = pex::util::read_uint<Uint>(data.substr(offset));
        offset += int_size;
        return value;
    }

    /// Read a sequence of byte and write it to a buffer pointed to by a forward iterator
    ///
    /// Buffer must have enough space to store `length` bytes, otherwise behavior is undefined
    ///
    /// @param length - Number of bytes to read
    /// @param begin - Forward iterator pointing to the beginning of the buffer
    ///
    /// @throws EofError if there is less than `length` bytes of data left to read
    ///
    /// Exception safety: strong guarantee: if an exception is thrown, DataReader object is unchanged and
    /// nothing is written to the buffer. HOWEVER, this guarantee is waived if *begin or ++begin throws.
    /// In such case (if *begin or ++begin throws) DataReader object's state is no longer considered valid.
    template <typename Iter>
    void read_bytes(size_t length, Iter begin)
    {

        if (get_number_of_bytes_left() < length) {
            throw EofError("not enough data to read " + std::to_string(length) + " bytes");
        }
        for (size_t i = 0; i < length; ++i) {
            auto byte = static_cast<uint8_t>(data[offset]);
            ++offset;
            *begin = byte;
            ++begin;
        }
    }

private:
    std::string_view data;
    size_t offset = 0;
};

} // namespace pex::data_reader

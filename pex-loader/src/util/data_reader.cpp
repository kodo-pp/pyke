#include <pex_loader/data_reader.hpp>


namespace pex::util
{

DataReader::EofError::EofError(const std::string& message):
    std::runtime_error(
        "Error reading data: premature end of file. Additional information: "
        + message
    )
{ }


size_t DataReader::get_offset() const noexcept
{
    return offset;
}


size_t DataReader::get_number_of_bytes_left() const noexcept
{
    return data.size() - offset;
}


void DataReader::skip(size_t length)
{
    if (get_number_of_bytes_left() < length) {
        throw EofError("cannot skip " + std::to_string(length) + " bytes");
    }
    offset += length;
}

}

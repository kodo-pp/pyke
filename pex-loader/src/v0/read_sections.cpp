#include <pex_loader/data_reader.hpp>
#include <pex_loader/pex_loader.hpp>

#include <cstdint>


namespace pex::loader::v0
{

std::vector<Section> read_sections(const std::string_view& data)
{
    pex::util::DataReader r(data);
    auto section_count = r.read_uint<uint64_t>();

    std::vector<Section> sections;
    sections.reserve(section_count);

    for (decltype(section_count) i = 0; i < section_count; ++i) {
        Section section;
        static_assert(section.name.size() == 4, "Section name length must be equal to 4");

        section.size = r.read_uint<uint64_t>() - 4;
        r.read_bytes(4, section.name.begin());
        section.offset = r.get_offset();

        sections.push_back(section);
        r.skip(section.size);
    }

    return sections;
}

}

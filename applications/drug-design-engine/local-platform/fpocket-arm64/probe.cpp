#include "molfile_plugin.h"
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
extern "C" {
int molfile_pdbxplugin_init();
int molfile_pdbxplugin_register(void *, vmdplugin_register_cb);
int molfile_pdbxplugin_fini();
int molfile_parm7plugin_init();
int molfile_parm7plugin_register(void *, vmdplugin_register_cb);
int molfile_parm7plugin_fini();
}
#ifndef EXPECTED_PLUGIN_ABI
#define EXPECTED_PLUGIN_ABI 18
#endif
static molfile_plugin_t *reader = nullptr;
static int register_reader(void *, vmdplugin_t *p) {
    reader = reinterpret_cast<molfile_plugin_t *>(p);
    return VMDPLUGIN_SUCCESS;
}
static void number(float x, bool present) {
    if (!present) std::cout << "null";
    else if (!std::isfinite(x)) throw std::runtime_error("non-finite value");
    else std::cout << x;
}
int main(int argc, char **argv) {
    if (argc != 3) return 64;
    const bool cif = std::string(argv[1]) == "pdbx";
    if (!cif && std::string(argv[1]) != "parm7") return 64;
    auto init = cif ? molfile_pdbxplugin_init : molfile_parm7plugin_init;
    auto reg = cif ? molfile_pdbxplugin_register : molfile_parm7plugin_register;
    auto fini = cif ? molfile_pdbxplugin_fini : molfile_parm7plugin_fini;
    if (init() != VMDPLUGIN_SUCCESS || reg(nullptr, register_reader) != VMDPLUGIN_SUCCESS ||
        !reader || reader->abiversion != EXPECTED_PLUGIN_ABI || !reader->open_file_read ||
        !reader->read_structure || !reader->close_file_read) return 65;
    int n = -1;
    void *handle = reader->open_file_read(argv[2], argv[1], &n);
    if (!handle || n <= 0 || n > 1000000) { fini(); return 66; }
    std::vector<molfile_atom_t> atoms(n);
    int flags = 0;
    if (reader->read_structure(handle, &flags, atoms.data()) != MOLFILE_SUCCESS) {
        reader->close_file_read(handle); fini(); return 67;
    }
    std::vector<float> xyz(n * 3);
    if (cif) {
        molfile_timestep_t ts{}; ts.coords = xyz.data();
        if (!reader->read_next_timestep || reader->read_next_timestep(handle,n,&ts) != MOLFILE_SUCCESS) {
            reader->close_file_read(handle); fini(); return 68;
        }
    }
    std::cout << std::setprecision(9);
    std::cout << "PROBE_JSON {\"abi\":" << reader->abiversion << ",\"reader\":"
              << std::quoted(reader->name) << ",\"natoms\":" << n << ",\"atoms\":[";
    for (int i=0; i<n; ++i) {
        const auto &a=atoms[i];
        if(i) std::cout << ',';
        std::cout << "{\"name\":" << std::quoted(a.name) << ",\"type\":" << std::quoted(a.type)
                  << ",\"resname\":" << std::quoted(a.resname) << ",\"resid\":" << a.resid
                  << ",\"chain\":" << std::quoted(a.chain) << ",\"mass\":";
        number(a.mass, flags & MOLFILE_MASS);
        std::cout << ",\"charge\":"; number(a.charge, flags & MOLFILE_CHARGE);
        std::cout << ",\"atomicnumber\":";
        if(flags & MOLFILE_ATOMICNUMBER) std::cout << a.atomicnumber; else std::cout << "null";
        std::cout << ",\"xyz\":";
        if(cif) {std::cout << '['; for(int j=0;j<3;++j) {if(j) std::cout << ','; number(xyz[i*3+j],true);} std::cout << ']';}
        else std::cout << "null";
        std::cout << '}';
    }
    std::cout << "],\"bonds\":";
    if (!cif && reader->read_bonds) {
        int count=0,*from=nullptr,*to=nullptr,*types=nullptr,ntypes=0;
        float *orders=nullptr; char **names=nullptr;
        if (reader->read_bonds(handle,&count,&from,&to,&orders,&types,&ntypes,&names)!=MOLFILE_SUCCESS) return 69;
        std::cout << '[';
        for(int i=0;i<count;++i) {if(i)std::cout << ',';std::cout << '[' << from[i] << ',' << to[i] << ']';}
        std::cout << ']';
    } else std::cout << "null";
    std::cout << "}\n";
    reader->close_file_read(handle);
    return fini()==VMDPLUGIN_SUCCESS ? 0 : 70;
}

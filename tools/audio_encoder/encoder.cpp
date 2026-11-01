// SPDX-License-Identifier: LGPL-2.1-or-later
// Thin PCM frontend to the separately licensed AtracDEnc encoder core.
#include "atrac3denc.h"
#include "env.h"
#include <filesystem>
#include <fstream>
#include <cmath>

class Output final : public ICompressedOutput {
    std::ofstream file;
    unsigned channels;
public:
    Output(const std::filesystem::path& path,unsigned count):file(path,std::ios::binary),channels(count) {
        if(!file)throw std::runtime_error("Cannot open encoded output");
    }
    std::string GetName()const override{return "";}
    size_t GetChannelNum()const override{return channels;}
    void WriteFrame(std::vector<char> bytes)override {
        if(bytes.size()!=304)throw std::runtime_error("Unexpected ATRAC frame size");
        if(channels==1 && !std::equal(bytes.begin(),bytes.begin()+152,bytes.begin()+152))
            throw std::runtime_error("Mono channel duplication differs");
        file.write(bytes.data(),152*channels);
        if(!file)throw std::runtime_error("Cannot write encoded frame");
    }
};

#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
#else
int main(int argc,char** argv) {
#endif
    try {
        if(argc!=4)throw std::runtime_error("Expected float PCM input, raw output and channel count");
        unsigned channels=std::filesystem::path(argv[3]).string()=="1"?1:2;
        std::ifstream input(std::filesystem::path(argv[1]),std::ios::binary);
        if(!input)throw std::runtime_error("Cannot open PCM input");
        const auto bytes=std::filesystem::file_size(argv[1]);
        if(!bytes || bytes%(4*channels))throw std::runtime_error("Invalid float PCM extent");
        NEnv::SetRoundFloat();
        NAtracDEnc::NAtrac3::TAtrac3EncoderSettings settings(104738,false,false,channels,0);
        if(settings.ConteinerParams->FrameSz!=304 || settings.ConteinerParams->Js)
            throw std::runtime_error("Encoder configuration changed");
        NAtracDEnc::TAtrac3Encoder encoder(std::make_unique<Output>(argv[2],channels),std::move(settings));
        auto process=encoder.GetLambda();
        const uint64_t frames=(bytes/(4*channels)+1023)/1024;
        std::vector<float> pcm(1024*channels);
        for(uint64_t frame=0;frame<frames+3;frame++) {
            std::fill(pcm.begin(),pcm.end(),0.f);
            if(frame<frames)input.read(reinterpret_cast<char*>(pcm.data()),pcm.size()*4);
            // AtracDEnc scales PCM by 1/4 before its analysis filters, so allow
            // samples through ±4 while rejecting values beyond its internal
            // unit-scale limit.
            for(float value:pcm)if(!std::isfinite(value) || std::abs(value)>4.0f)
                throw std::runtime_error("PCM sample exceeds the ATRAC encoder input range (±4.0)");
            process(pcm.data(),TPCMEngine::ProcessMeta{static_cast<uint16_t>(channels)});
        }
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<std::endl;return 1;}
}

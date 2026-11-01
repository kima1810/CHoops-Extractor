/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 CHoops contributors
 * Independent bounded H7A/LZSS encoder and decoder. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif
#define ERROR ((size_t)-1)
API uint32_t h7a_version(void) { return 2; }
static uint32_t be32(const uint8_t *p) { return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3]; }
API size_t h7a_decode(const uint8_t *src,size_t size,uint8_t *out,size_t capacity) {
    if(size<20 || be32(src)!=0x0e4837c3 || be32(src+8)!=size) return ERROR;
    size_t expected=be32(src+4);uint32_t shift=be32(src+16);
    if(expected>capacity || shift<1 || shift>16) return ERROR;
    uint32_t mask=(1u<<shift)-1;size_t p=20,n=0;
    while(n<expected) {
        if(p>=size) return ERROR;uint8_t flags=src[p++];
        for(unsigned bit=0;bit<8 && n<expected;bit++) {
            if(flags&(1u<<bit)) {
                if(size-p<2) return ERROR;uint32_t token=((uint32_t)src[p]<<8)|src[p+1];p+=2;
                size_t distance=token&mask,length=(token>>shift)+3;
                if(!distance || distance>n) return ERROR;
                if(length>expected-n) length=expected-n;
                for(size_t i=0;i<length;i++) {out[n]=out[n-distance];n++;}
            } else {if(p>=size) return ERROR;out[n++]=src[p++];}
        }
    }
    return n;
}
static uint32_t hash3(const uint8_t *p) {
    uint32_t key=p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16);
    return (key*2654435761u)>>16;
}
API uint32_t h7a_game_compatible(const uint8_t *src,size_t size) {
    if(size<20 || be32(src)!=0x0e4837c3 || be32(src+8)!=size) return 0;
    size_t expected=be32(src+4),n=0,p=20;uint32_t shift=be32(src+16);
    if(expected>0x20000000u || shift<1 || shift>16) return 0;
    uint32_t mask=(1u<<shift)-1;
    while(n<expected) {
        if(p>=size) return 0;uint8_t flags=src[p++];
        for(unsigned bit=0;bit<8 && n<expected;bit++) {
            if(flags&(1u<<bit)) {
                if(size-p<2) return 0;uint32_t token=((uint32_t)src[p]<<8)|src[p+1];p+=2;
                size_t distance=token&mask,length=(token>>shift)+3;
                if(length>expected-n) length=expected-n;
                if(!distance || distance>n || length>distance) return 0;n+=length;
            } else {if(p>=size) return 0;p++;n++;}
        }
    }
    return 1;
}
API size_t h7a_encode(const uint8_t *src,size_t size,uint32_t shift,uint8_t *out,size_t capacity) {
    if(shift<1 || shift>16 || size>0x20000000u) return ERROR;
    uint32_t *heads=(uint32_t*)calloc(65536,sizeof(uint32_t));
    uint32_t *links=(uint32_t*)calloc(65536,sizeof(uint32_t));
    if(!heads || !links) {free(heads);free(links);return ERROR;}
    size_t p=0,n=0,group=0;unsigned bit=8;uint32_t max_distance=(1u<<shift)-1;
    size_t max_length=(0xffffu>>shift)+3;
    while(p<size) {
        if(bit==8) {if(n>=capacity) goto fail;group=n;out[n++]=0;bit=0;}
        size_t best=0,distance=0,limit=size-p<max_length?size-p:max_length;
        if(limit>=3) {
            uint32_t candidate=heads[hash3(src+p)];unsigned searched=0;
            while(candidate && searched++<32) {
                size_t old=(size_t)candidate-1;
                if(old>=p || p-old>max_distance) break;
                size_t candidate_limit=limit<p-old?limit:p-old;
                if(candidate_limit<3) {uint32_t next=links[old&65535];if(next>=candidate) break;candidate=next;continue;}
                if(src[old]==src[p] && src[old+1]==src[p+1] && src[old+2]==src[p+2]) {
                    size_t length=3;
                    while(length<candidate_limit && src[p+length]==src[p+length-(p-old)]) length++;
                    if(length>best) {best=length;distance=p-old;}
                    if(length==limit) break;
                }
                uint32_t next=links[old&65535];if(next>=candidate) break;candidate=next;
            }
        }
        size_t consumed;
        if(best>=3) {
            if(capacity-n<2) goto fail;
            uint32_t token=((uint32_t)(best-3)<<shift)|(uint32_t)distance;
            out[group]|=(uint8_t)(1u<<bit);out[n++]=(uint8_t)(token>>8);out[n++]=(uint8_t)token;consumed=best;
        } else {if(n>=capacity) goto fail;out[n++]=src[p];consumed=1;}
        for(size_t at=p;at<p+consumed;at++) {
            if(size-at>=3) {uint32_t h=hash3(src+at);links[at&65535]=heads[h];heads[h]=(uint32_t)at+1;}
        }
        p+=consumed;bit++;
    }
    free(heads);free(links);return n;
fail:
    free(heads);free(links);return ERROR;
}

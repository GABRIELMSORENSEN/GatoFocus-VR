#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dxgi.h>
#include <wrl/client.h>
#include <string>
#include <cstring>
#include "openvr.h"
using Microsoft::WRL::ComPtr;
static vr::IVRSystem* systemVR = nullptr;
static ComPtr<ID3D11Device> device;
static ComPtr<ID3D11DeviceContext> context;
static ComPtr<ID3D11Texture2D> target, staging;
static ComPtr<ID3D11RenderTargetView> rtv;
static ComPtr<ID3D11VertexShader> vs;
static ComPtr<ID3D11PixelShader> ps;
static ComPtr<ID3D11PixelShader> psGamma;
static ComPtr<ID3D11SamplerState> sampler;
static ID3D11ShaderResourceView* mirror = nullptr;
static std::string error;
static constexpr unsigned EDGE = 416;
#define API extern "C" __declspec(dllexport)
API const char* gf_error() { return error.c_str(); }
API void gf_close() {
  if (mirror && vr::VRCompositor()) vr::VRCompositor()->ReleaseMirrorTextureD3D11(mirror);
  mirror = nullptr;
  sampler.Reset(); psGamma.Reset(); ps.Reset(); vs.Reset(); rtv.Reset(); staging.Reset(); target.Reset();
  context.Reset(); device.Reset();
  if (systemVR) vr::VR_Shutdown();
  systemVR = nullptr;
}
static bool check(HRESULT hr, const char* op) {
  if (SUCCEEDED(hr)) return true;
  error = std::string(op) + " (" + std::to_string((unsigned)hr) + ")";
  return false;
}
API int gf_open() {
  gf_close();
  vr::EVRInitError e;
  systemVR = vr::VR_Init(&e, vr::VRApplication_Overlay);
  if (e != vr::VRInitError_None) {
    error = vr::VR_GetVRInitErrorAsEnglishDescription(e); systemVR = nullptr; return 0;
  }
  int adapterIndex = -1;
  systemVR->GetDXGIOutputInfo(&adapterIndex);
  ComPtr<IDXGIFactory1> factory;
  ComPtr<IDXGIAdapter> adapter;
  if (!check(CreateDXGIFactory1(IID_PPV_ARGS(&factory)), "DXGI")) return 0;
  if (adapterIndex >= 0) factory->EnumAdapters(adapterIndex, &adapter);
  if (!check(D3D11CreateDevice(adapter.Get(), adapter ? D3D_DRIVER_TYPE_UNKNOWN : D3D_DRIVER_TYPE_HARDWARE,
      nullptr, D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION,
      &device, nullptr, &context), "D3D11")) return 0;
  D3D11_TEXTURE2D_DESC desc{};
  desc.Width = desc.Height = EDGE; desc.MipLevels = desc.ArraySize = 1;
  desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM; desc.SampleDesc.Count = 1;
  desc.BindFlags = D3D11_BIND_RENDER_TARGET;
  if (!check(device->CreateTexture2D(&desc, nullptr, &target), "Target")) return 0;
  if (!check(device->CreateRenderTargetView(target.Get(), nullptr, &rtv), "RTV")) return 0;
  desc.BindFlags = 0; desc.Usage = D3D11_USAGE_STAGING; desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
  if (!check(device->CreateTexture2D(&desc, nullptr, &staging), "Staging")) return 0;
  const char* shader = R"(
struct V { float4 pos:SV_POSITION; float2 uv:TEXCOORD0; };
V vert(uint id:SV_VertexID) { V o; o.uv=float2((id<<1)&2,id&2); o.pos=float4(o.uv*float2(2,-2)+float2(-1,1),0,1); return o; }
Texture2D image:register(t0); SamplerState smp:register(s0);
float4 pixel(V i):SV_TARGET { return float4(image.Sample(smp,i.uv).rgb,1); }
float4 pixelGamma(V i):SV_TARGET {
  float3 c=max(image.Sample(smp,i.uv).rgb,0);
  return float4(lerp(12.92*c,1.055*pow(c,1.0/2.4)-0.055,step(0.0031308,c)),1);
}
)";
  ComPtr<ID3DBlob> code, messages;
  if (!check(D3DCompile(shader, strlen(shader), nullptr, nullptr, nullptr, "vert", "vs_4_0", 0, 0, &code, &messages), "Vertex compile")) return 0;
  if (!check(device->CreateVertexShader(code->GetBufferPointer(), code->GetBufferSize(), nullptr, &vs), "Vertex shader")) return 0;
  code.Reset(); messages.Reset();
  if (!check(D3DCompile(shader, strlen(shader), nullptr, nullptr, nullptr, "pixel", "ps_4_0", 0, 0, &code, &messages), "Pixel compile")) return 0;
  if (!check(device->CreatePixelShader(code->GetBufferPointer(), code->GetBufferSize(), nullptr, &ps), "Pixel shader")) return 0;
  code.Reset(); messages.Reset();
  if (!check(D3DCompile(shader, strlen(shader), nullptr, nullptr, nullptr, "pixelGamma", "ps_4_0", 0, 0, &code, &messages), "Gamma compile")) return 0;
  if (!check(device->CreatePixelShader(code->GetBufferPointer(), code->GetBufferSize(), nullptr, &psGamma), "Gamma shader")) return 0;
  D3D11_SAMPLER_DESC sd{};
  sd.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
  sd.AddressU = sd.AddressV = sd.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
  sd.MaxLOD = D3D11_FLOAT32_MAX;
  if (!check(device->CreateSamplerState(&sd, &sampler), "Sampler")) return 0;
  error.clear(); return 1;
}
// Returns BGRA and left-eye projection bounds. No game hooks or driver changes.
API int gf_grab(unsigned char* output, unsigned length, float* projection, float* eyeRotation, unsigned* scenePid) {
  if (!systemVR || !device || length < EDGE*EDGE*4) { error="Capture not initialized"; return 0; }
  auto comp=vr::VRCompositor();
  if (!comp) { error="Compositor unavailable"; return 0; }
  *scenePid=comp->GetCurrentSceneFocusProcess();
  if (!mirror) {
    auto e=comp->GetMirrorTextureD3D11(vr::Eye_Left, device.Get(), (void**)&mirror);
    if (e!=vr::VRCompositorError_None || !mirror) { error="Mirror unavailable: "+std::to_string(e); return 0; }
  }
  D3D11_VIEWPORT vp{0,0,(float)EDGE,(float)EDGE,0,1};
  context->RSSetViewports(1,&vp);
  ID3D11RenderTargetView* rt=rtv.Get(); context->OMSetRenderTargets(1,&rt,nullptr);
  context->IASetInputLayout(nullptr); context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  D3D11_SHADER_RESOURCE_VIEW_DESC viewDesc{}; mirror->GetDesc(&viewDesc);
  bool srgb = viewDesc.Format == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB || viewDesc.Format == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB || viewDesc.Format == DXGI_FORMAT_B8G8R8X8_UNORM_SRGB;
  context->VSSetShader(vs.Get(),nullptr,0); context->PSSetShader(srgb ? psGamma.Get() : ps.Get(),nullptr,0);
  ID3D11SamplerState* sam=sampler.Get(); context->PSSetSamplers(0,1,&sam);
  context->PSSetShaderResources(0,1,&mirror);
  context->Draw(3,0);
  ID3D11ShaderResourceView* empty=nullptr; context->PSSetShaderResources(0,1,&empty);
  context->CopyResource(staging.Get(),target.Get());
  D3D11_MAPPED_SUBRESOURCE mapped{};
  if (!check(context->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped),"Readback")) return 0;
  for(unsigned y=0;y<EDGE;y++) memcpy(output+y*EDGE*4,(char*)mapped.pData+y*mapped.RowPitch,EDGE*4);
  context->Unmap(staging.Get(),0);
  systemVR->GetProjectionRaw(vr::Eye_Left,projection,projection+1,projection+2,projection+3);
  auto rot=systemVR->GetEyeToHeadTransform(vr::Eye_Left);
  for(int r=0;r<3;r++) for(int c=0;c<3;c++) eyeRotation[r*3+c]=rot.m[r][c];
  error.clear(); return 1;
}

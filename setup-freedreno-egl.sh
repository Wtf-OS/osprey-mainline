#!/sbin/sh
set -e
# init uses umask 077; these overlays must be readable by apps/system_server.
umask 022
export LD_LIBRARY_PATH=/data/graphics-libs:/system/lib:/system/lib/bootstrap:/vendor/lib
export PATH=/system/bin:/sbin
mkdir -p /data/probe-egl-freedreno
chmod 0755 /data/probe-egl-freedreno /data/graphics-libs /data/mesa-libs
for api in EGL GLESv1_CM GLESv2; do
    cp /data/mesa-libs/lib${api}_adreno.so /data/probe-egl-freedreno/lib${api}_adreno.so.new
    mv /data/probe-egl-freedreno/lib${api}_adreno.so.new /data/probe-egl-freedreno/lib${api}_adreno.so
done
for name in libgallium_dri.so libglapi.so libdrm.so libdrm_freedreno.so; do
    if [ -f /data/graphics-libs/$name ] && [ ! -f /data/graphics-libs/$name.before-freedreno ]; then
        cp /data/graphics-libs/$name /data/graphics-libs/$name.before-freedreno
    fi
    cp /data/mesa-libs/$name /data/probe-egl-freedreno/$name.new
    mv /data/probe-egl-freedreno/$name.new /data/probe-egl-freedreno/$name
    cp /data/mesa-libs/$name /data/graphics-libs/$name.new
    mv /data/graphics-libs/$name.new /data/graphics-libs/$name
done
# GLSL types now remain alive until asynchronous shader workers finish.
setprop mesa.fd.mesa.debug ""
mount --bind /data/probe-egl-freedreno /vendor/lib/egl

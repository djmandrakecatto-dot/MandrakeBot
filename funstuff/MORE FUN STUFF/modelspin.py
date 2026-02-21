import discord
from discord.ext import commands
import io, math, os
import numpy as np
from PIL import Image, ImageDraw
from pygltflib import GLTF2
import asyncio

class GLBLoader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_glb_data(self, gltf, single_tex=False):
        binary_blob = gltf.binary_blob()
        vertices, indices, uvs = [], [], []
        vertex_offset = 0 
        tex_image = None

        # 1. Texture Atlas Extraction
        if single_tex and gltf.images:
            try:
                # We grab the first image (usually gltf_Texture.png in an atlas)
                img_meta = gltf.images[0]
                if img_meta.bufferView is not None:
                    bv = gltf.bufferViews[img_meta.bufferView]
                    img_bytes = binary_blob[bv.byteOffset : bv.byteOffset + bv.byteLength]
                    tex_image = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            except Exception as e:
                print(f"Atlas Load Error: {e}")

        for mesh in gltf.meshes:
            for primitive in mesh.primitives:
                # 2. Extract Vertices
                pos_acc = gltf.accessors[primitive.attributes.POSITION]
                pos_bv = gltf.bufferViews[pos_acc.bufferView]
                v_start = (pos_bv.byteOffset or 0) + (pos_acc.byteOffset or 0)
                
                points = np.frombuffer(
                    binary_blob[v_start : v_start + pos_acc.count * 12], 
                    dtype=np.float32
                ).reshape(-1, 3).copy()
                vertices.extend(points)

                # 3. Extract UVs (The texture positions)
                if single_tex and hasattr(primitive.attributes, "TEXCOORD_0"):
                    uv_acc = gltf.accessors[primitive.attributes.TEXCOORD_0]
                    uv_bv = gltf.bufferViews[uv_acc.bufferView]
                    u_start = (uv_bv.byteOffset or 0) + (uv_acc.byteOffset or 0)
                    
                    uv_data = np.frombuffer(
                        binary_blob[u_start : u_start + uv_acc.count * 8], 
                        dtype=np.float32
                    ).reshape(-1, 2).copy()
                    
                    # Flip V for Pillow (Standard for GLB -> PIL)
                    uv_data[:, 1] = 1.0 - uv_data[:, 1]
                    uvs.extend(uv_data)
                else:
                    # Keep lists synced even if a part has no UVs
                    uvs.extend(np.zeros((len(points), 2)))

                # 4. Extract Indices with Global Offset
                if primitive.indices is not None:
                    idx_acc = gltf.accessors[primitive.indices]
                    idx_bv = gltf.bufferViews[idx_acc.bufferView]
                    i_start = (idx_bv.byteOffset or 0) + (idx_acc.byteOffset or 0)
                    
                    id_dtype = np.uint16 if idx_acc.componentType == 5123 else np.uint32
                    idx = np.frombuffer(
                        binary_blob[i_start : i_start + idx_acc.count * np.dtype(id_dtype).itemsize], 
                        dtype=id_dtype
                    ).copy()
                    
                    # Offset ensures indices point to the correct Vertex/UV pair
                    idx = (idx.astype(np.uint32) + vertex_offset).reshape(-1, 3)
                    indices.extend(idx)

                vertex_offset += len(points)

        return np.array(vertices), indices, np.array(uvs), tex_image

    @commands.command(name="loadglb")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def loadglb(self, ctx, *args):
        """Usage: !loadglb singletexture=True"""
        arg_str = " ".join(args).lower()
        single_tex = "singletexture=true" in arg_str
        
        if not ctx.message.attachments:
            return await ctx.send("📦 Attach your `.glb` model!")

        async with self.bot.process_queue:
            status = await ctx.send("⚙️ Parsing Mesh & Texture Atlas...")
            try:
                attachment = ctx.message.attachments[0]
                glb_bytes = await attachment.read()
                
                # Load GLB
                gltf = GLTF2.load_from_bytes(glb_bytes)
                
                loop = asyncio.get_event_loop()
                # Run the math-heavy render in a thread
                result = await loop.run_in_executor(None, self.render_process, gltf, single_tex)
                
                await status.delete()
                await ctx.send(file=discord.File(result, filename="render.gif"))

            except Exception as e:
                await ctx.send(f"⚠️ GLB Error: {e}")

    def render_process(self, gltf, single_tex):
        vertices, indices, uvs, tex_img = self.get_glb_data(gltf, single_tex)

        # Normalize 3D points
        vertices -= np.mean(vertices, axis=0)
        vertices /= (np.max(np.abs(vertices)) or 1.0)

        frames = []
        size = (400, 400)
        
        # Projection Math
        def project(v, angle):
            rad = math.radians(angle)
            c, s = math.cos(rad), math.sin(rad)
            rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
            rotated = v @ rot.T
            rotated[:, 2] += 2.5 
            f = 400 / rotated[:, 2]
            return np.column_stack(((rotated[:, 0] * f) + 200, (rotated[:, 1] * f) + 200)), rotated[:, 2]

        for angle in range(0, 360, 45):
            canvas = Image.new("RGBA", size, (12, 12, 12, 255))
            draw = ImageDraw.Draw(canvas)
            points, depths = project(vertices, angle)

            # Sort faces by depth (back-to-front)
            face_depths = [np.mean([depths[i] for i in face]) for face in indices]
            sorted_idx = sorted(zip(indices, face_depths), key=lambda x: x[1], reverse=True)

            for face, d in sorted_idx:
                poly = [tuple(points[i]) for i in face]
                color = (0, 255, 0, 100) # Default if no texture

                if single_tex and tex_img and uvs.size > 0:
                    # Pull UVs for the vertices in this specific face
                    f_uvs = uvs[face]
                    u, v = np.mean(f_uvs[:, 0]), np.mean(f_uvs[:, 1])
                    tx = int((u % 1.0) * (tex_img.width - 1))
                    ty = int((v % 1.0) * (tex_img.height - 1))
                    color = tex_img.getpixel((tx, ty))

                draw.polygon(poly, fill=color)
            
            frames.append(canvas)

        out = io.BytesIO()
        frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
        out.seek(0)
        return out

async def setup(bot):
    await bot.add_cog(GLBLoader(bot))
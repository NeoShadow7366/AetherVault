import pytest
import sys
import os

# Allow import of backend module
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(os.path.dirname(current_dir), ".backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from proxy_translators import build_comfy_workflow, build_a1111_payload, build_fooocus_payload

def test_a1111_sampler_translation():
    """Assert SD WebUI sampler mapping mathematically translates."""
    payload = {
        "sampler_name": "dpmpp_2m_sde",
        "prompt": "Test Prompt",
        "steps": 20
    }
    result = build_a1111_payload(payload)
    assert result["sampler_name"] == "DPM++ 2M SDE"

def test_a1111_lora_string_concatenation():
    """Assert SD WebUI concatenates loras securely without .safetensors."""
    payload = {
        "prompt": "Test Prompt",
        "loras": [
            {"name": "my_lora.safetensors", "weight": 0.8},
            {"name": "second_lora", "weight": 1.2}
        ]
    }
    result = build_a1111_payload(payload)
    # The lora extensions should be stripped and formatted <lora:name:weight>
    assert "<lora:my_lora:0.8>" in result["prompt"]
    assert "<lora:second_lora:1.2>" in result["prompt"]

def test_a1111_img2img_hires():
    """Assert SD WebUI resolves Img2Img and Hires cleanly."""
    payload = {
        "prompt": "Img",
        "init_image_b64": "data:image/png;base64,mock",
        "denoising_strength": 0.7,
        "hires": {"enable": True, "factor": 1.5, "upscaler": "Latent"}
    }
    result = build_a1111_payload(payload)
    # If init_image is passed, enable_hr MUST be false (A1111 limitation)
    assert "init_images" in result
    assert result["init_images"] == ["data:image/png;base64,mock"]
    assert "enable_hr" not in result

def test_comfy_flux_graph():
    """Assert FLUX builds unique node graphs (UNETLoader / DualCLIP)."""
    payload = {
        "prompt": "FLUX test",
        "model_type": "flux-dev",
        "override_settings": {"sd_model_checkpoint": "flux1-dev.safetensors"},
        "flux_clip_l": "clip_l.safetensors",
        "flux_t5xxl": "t5_xxl.safetensors"
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    assert "11" in graph
    assert graph["11"]["class_type"] == "UNETLoader"
    assert graph["11"]["inputs"]["unet_name"] == "flux1-dev.safetensors"
    
    assert "12" in graph
    assert graph["12"]["class_type"] == "DualCLIPLoader"
    assert graph["12"]["inputs"]["clip_name1"] == "t5_xxl.safetensors"
    assert graph["12"]["inputs"]["clip_name2"] == "clip_l.safetensors"

def test_comfy_sdxl_graph():
    """Assert SDXL builds CheckpointLoader templates with standard inputs."""
    payload = {
        "prompt": "SDXL test",
        "model_type": "sdxl",
        "override_settings": {"sd_model_checkpoint": "sdxl_base.safetensors"}
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    assert "4" in graph
    assert graph["4"]["class_type"] == "CheckpointLoaderSimple"
    assert graph["4"]["inputs"]["ckpt_name"] == "sdxl_base.safetensors"
    
    # Assert missing UNETLoader, proving SDXL branch executed
    assert "11" not in graph

def test_comfy_refiner_injection():
    """Assert SDXL utilizes secondary KSampler and Checkpoint for refiners."""
    payload = {
        "prompt": "Refiner Test",
        "model_type": "sdxl",
        "override_settings": {"sd_model_checkpoint": "sdxl_base.safetensors"},
        "refiner": "sdxl_refiner.safetensors",
        "steps": 20,
        "refiner_steps": 10
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    # Base sampler
    assert "3" in graph
    assert graph["3"]["class_type"] == "KSamplerAdvanced"
    
    # Refiner checkpoint
    assert "202" in graph
    assert graph["202"]["class_type"] == "CheckpointLoaderSimple"
    assert graph["202"]["inputs"]["ckpt_name"] == "sdxl_refiner.safetensors"

def test_fooocus_mapping():
    """Assert Fooocus payload map operates correctly."""
    result = build_fooocus_payload({"prompt": "Fooocus", "width": 1024, "height": 1024})
    assert result["prompt"] == "Fooocus"
    assert result["aspect_ratios_selection"] == "1024*1024"


# ── Sprint 12: Inpainting Mask Tests ─────────────────────────────────

def test_comfy_flux_inpainting_mask():
    """Assert FLUX inpainting injects LoadImageMask + SetLatentNoiseMask when mask_image_name is provided."""
    payload = {
        "prompt": "inpaint test",
        "model_type": "flux-dev",
        "override_settings": {"sd_model_checkpoint": "flux1-dev.safetensors"},
        "flux_clip_l": "clip_l.safetensors",
        "flux_t5xxl": "t5_xxl.safetensors",
        "init_image_name": "source.png",
        "mask_image_name": "mask.png",
        "denoising_strength": 0.75
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    # LoadImage for source
    assert "1001" in graph
    assert graph["1001"]["class_type"] == "LoadImage"
    
    # VAEEncode for source
    assert "1002" in graph
    assert graph["1002"]["class_type"] == "VAEEncode"
    
    # LoadImageMask for mask
    assert "2001" in graph
    assert graph["2001"]["class_type"] == "LoadImageMask"
    assert graph["2001"]["inputs"]["image"] == "mask.png"
    
    # SetLatentNoiseMask connects mask to latent
    assert "2002" in graph
    assert graph["2002"]["class_type"] == "SetLatentNoiseMask"
    assert graph["2002"]["inputs"]["samples"] == ["1002", 0]
    assert graph["2002"]["inputs"]["mask"] == ["2001", 0]
    
    # KSampler should use the masked latent as input
    assert graph["18"]["inputs"]["latent_image"] == ["2002", 0]


def test_comfy_sdxl_inpainting_mask():
    """Assert SDXL inpainting injects LoadImageMask + SetLatentNoiseMask."""
    payload = {
        "prompt": "sdxl inpaint",
        "model_type": "sdxl",
        "override_settings": {"sd_model_checkpoint": "sdxl_base.safetensors"},
        "init_image_name": "source.png",
        "mask_image_name": "mask.png",
        "denoising_strength": 0.7
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    # LoadImageMask
    assert "2001" in graph
    assert graph["2001"]["class_type"] == "LoadImageMask"
    
    # SetLatentNoiseMask
    assert "2002" in graph
    assert graph["2002"]["class_type"] == "SetLatentNoiseMask"
    
    # KSampler (node 3 in SDXL) should use masked latent
    assert graph["3"]["inputs"]["latent_image"] == ["2002", 0]


# ── Sprint 12: Regional Prompting Tests ──────────────────────────────

def test_comfy_flux_regional_prompting():
    """Assert FLUX regional prompting builds CLIPTextEncode → FluxGuidance → ConditioningSetArea → ConditioningCombine chain."""
    payload = {
        "prompt": "global prompt",
        "model_type": "flux-dev",
        "override_settings": {"sd_model_checkpoint": "flux1-dev.safetensors"},
        "flux_clip_l": "clip_l.safetensors",
        "flux_t5xxl": "t5_xxl.safetensors",
        "width": 1024,
        "height": 1024,
        "regions": [
            {"prompt": "a blue sky", "x": 0.0, "y": 0.0, "w": 1.0, "h": 0.5},
            {"prompt": "green grass", "x": 0.0, "y": 0.5, "w": 1.0, "h": 0.5}
        ]
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    # Region 1: CLIPTextEncode(3001) → FluxGuidance(3002) → ConditioningSetArea(3003)
    assert "3001" in graph
    assert graph["3001"]["class_type"] == "CLIPTextEncode"
    assert graph["3001"]["inputs"]["text"] == "a blue sky"
    
    assert "3002" in graph
    assert graph["3002"]["class_type"] == "FluxGuidance"
    
    assert "3003" in graph
    assert graph["3003"]["class_type"] == "ConditioningSetArea"
    # Verify pixel coordinates: x=0*1024=0, y=0*1024=0, w=1024, h=512
    assert graph["3003"]["inputs"]["x"] == 0
    assert graph["3003"]["inputs"]["y"] == 0
    assert graph["3003"]["inputs"]["width"] == 1024
    assert graph["3003"]["inputs"]["height"] == 512
    
    # Region 2: CLIPTextEncode(3004) → FluxGuidance(3005) → ConditioningSetArea(3006)
    assert "3004" in graph
    assert graph["3004"]["inputs"]["text"] == "green grass"
    
    assert "3006" in graph
    assert graph["3006"]["class_type"] == "ConditioningSetArea"
    assert graph["3006"]["inputs"]["y"] == 512
    
    # ConditioningCombine(3007) merges both regions
    assert "3007" in graph
    assert graph["3007"]["class_type"] == "ConditioningCombine"
    assert graph["3007"]["inputs"]["conditioning_1"] == ["3003", 0]
    assert graph["3007"]["inputs"]["conditioning_2"] == ["3006", 0]
    
    # KSampler should use the combined conditioning as positive
    assert graph["18"]["inputs"]["positive"] == ["3007", 0]


def test_comfy_sdxl_regional_prompting():
    """Assert SDXL regional prompting builds CLIPTextEncode → ConditioningSetArea → ConditioningCombine (no FluxGuidance)."""
    payload = {
        "prompt": "global prompt",
        "model_type": "sdxl",
        "override_settings": {"sd_model_checkpoint": "sdxl_base.safetensors"},
        "width": 1024,
        "height": 1024,
        "regions": [
            {"prompt": "left side", "x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0},
            {"prompt": "right side", "x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0}
        ]
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    # Region 1: CLIPTextEncode(3001) → ConditioningSetArea(3002) — NO FluxGuidance
    assert "3001" in graph
    assert graph["3001"]["class_type"] == "CLIPTextEncode"
    assert graph["3001"]["inputs"]["text"] == "left side"
    
    assert "3002" in graph
    assert graph["3002"]["class_type"] == "ConditioningSetArea"
    assert graph["3002"]["inputs"]["width"] == 512
    assert graph["3002"]["inputs"]["height"] == 1024
    
    # Region 2: CLIPTextEncode(3003) → ConditioningSetArea(3004)
    assert "3003" in graph
    assert "3004" in graph
    assert graph["3004"]["class_type"] == "ConditioningSetArea"
    assert graph["3004"]["inputs"]["x"] == 512
    
    # ConditioningCombine(3005) merges
    assert "3005" in graph
    assert graph["3005"]["class_type"] == "ConditioningCombine"
    
    # KSampler (node 3) should use combined conditioning
    assert graph["3"]["inputs"]["positive"] == ["3005", 0]


def test_comfy_flux_single_region():
    """Assert a single region does NOT produce ConditioningCombine."""
    payload = {
        "prompt": "global",
        "model_type": "flux-dev",
        "override_settings": {"sd_model_checkpoint": "flux1-dev.safetensors"},
        "flux_clip_l": "clip_l.safetensors",
        "flux_t5xxl": "t5_xxl.safetensors",
        "width": 1024,
        "height": 1024,
        "regions": [
            {"prompt": "only zone", "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
        ]
    }
    workflow = build_comfy_workflow(payload)
    graph = workflow.get("prompt", {})
    
    # Single region chain: CLIPTextEncode(3001) → FluxGuidance(3002) → ConditioningSetArea(3003)
    assert "3001" in graph
    assert "3002" in graph
    assert "3003" in graph
    assert graph["3003"]["class_type"] == "ConditioningSetArea"
    
    # No ConditioningCombine needed for a single region
    assert "3004" not in graph
    
    # KSampler uses the single region's area conditioning directly
    assert graph["18"]["inputs"]["positive"] == ["3003", 0]


# ── Sprint 12: A1111 Inpainting & Regional Tests ────────────────────

def test_a1111_inpainting_payload():
    """Assert A1111 inpainting sets mask, inpainting_fill, mask_blur, and inpaint_full_res fields."""
    payload = {
        "prompt": "inpaint test",
        "init_image_b64": "data:image/png;base64,mock_b64_data",
        "mask_b64": "data:image/png;base64,mock_mask_data",
        "denoising_strength": 0.75
    }
    result = build_a1111_payload(payload)
    
    assert "init_images" in result
    assert result["init_images"] == ["data:image/png;base64,mock_b64_data"]
    assert result["denoising_strength"] == 0.75
    
    # Sprint 12 mask fields
    assert result["mask"] == "data:image/png;base64,mock_mask_data"
    assert result["inpainting_fill"] == 1
    assert result["mask_blur"] == 4
    assert result["inpaint_full_res"] == True
    assert result["inpaint_full_res_padding"] == 32
    
    # Hires should NOT be enabled when init_image is present
    assert "enable_hr" not in result


def test_a1111_regional_prompting_break():
    """Assert A1111 regional prompting joins zone prompts with BREAK delimiters."""
    payload = {
        "prompt": "global context",
        "regions": [
            {"prompt": "zone one details"},
            {"prompt": "zone two details"},
            {"prompt": ""}  # Empty zone should be skipped
        ]
    }
    result = build_a1111_payload(payload)
    
    # Prompt should be: "global context BREAK zone one details BREAK zone two details"
    assert "BREAK" in result["prompt"]
    assert "zone one details" in result["prompt"]
    assert "zone two details" in result["prompt"]
    assert result["prompt"].count("BREAK") == 2


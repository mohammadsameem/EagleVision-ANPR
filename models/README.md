# EagleVision ANPR - Model Directory

This directory contains AI models used in the ANPR pipeline.

## Models

### License Plate Detection Model

**Model:** YOLOv8n License Plate Detector  
**Source:** [Koushim/yolov8-license-plate-detection](https://huggingface.co/Koushim/yolov8-license-plate-detection)  
**File:** `plate_detector.pt` (downloaded as `best.pt` from source)  
**Size:** 6.25 MB  
**Architecture:** YOLOv8n (Nano variant)  
**Task:** Single-class object detection (license_plate)  
**Input Resolution:** 640×640  

#### Licensing Information

**Model Weights License:** MIT  
Per the Hugging Face model card metadata, the trained weights are licensed under MIT.

**Framework License:** Ultralytics AGPL-3.0  
The YOLOv8 framework (ultralytics package) is licensed under AGPL-3.0.

**AGPL-3.0 Implications:**
- Content is rephrased for compliance with licensing restrictions
- AGPL requires that derivative works be released under AGPL
- Commercial use may require Ultralytics Enterprise License
- For development and testing, AGPL-3.0 is typically acceptable
- Production deployment should verify licensing requirements

**Source:** [Ultralytics License Information](https://www.ultralytics.com/license)

#### Training Data

**Note:** Training dataset not documented in model repository. Regional accuracy may vary.

Per Intel's license-plate-recognition model documentation: "Plate detector accuracy depends on the regional distribution of training data."

For Indian registration plates specifically, accuracy should be validated and the model may require fine-tuning on representative Indian plate data.

#### Download Information

**Downloaded:** 2026-10-28  
**Method:** Direct download from Hugging Face repository  
**URL:** https://huggingface.co/Koushim/yolov8-license-plate-detection/resolve/main/best.pt

#### Model Performance (To Be Validated)

- Precision: Unknown (to be measured on test data)
- Recall: Unknown (to be measured on test data)
- mAP50: Unknown (to be measured on test data)
- Inference speed: To be benchmarked

#### Verification Checklist

- [x] Model source identified and documented
- [x] License information verified (MIT for weights, AGPL-3.0 for framework)
- [x] Download URL confirmed
- [ ] Model downloaded and validated
- [ ] Tested on sample vehicle crops
- [ ] Performance measured on test dataset
- [ ] Regional suitability for Indian plates assessed

---

## Model Management

### Adding New Models

When adding new models to this directory:

1. Document the source repository/paper
2. Verify and document licensing (weights, framework, training data)
3. Record download URL and date
4. Note model size, architecture, and task
5. Test on validation data before integration
6. Update this README with results

### License Compliance

All models must have clear licensing documentation. For production use:

- Verify commercial use permissions
- Check training data restrictions
- Ensure framework license compatibility
- Document any required attributions

---

## References

- [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
- [Hugging Face Model Repository](https://huggingface.co/Koushim/yolov8-license-plate-detection)
- [Ultralytics Licensing](https://www.ultralytics.com/license)

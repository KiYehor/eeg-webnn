
export async function loadONNXModel(modelPath) {
  const session = await ort.InferenceSession.create(modelPath);

  return {
    compute: async (inputs) => {
      const inputTensors = {};
      for (const key in inputs) {
        inputTensors[key] = new ort.Tensor('float32', inputs[key], [1, inputs[key].length]);
      }
      const output = await session.run(inputTensors);
      return output;
    }
  };
}
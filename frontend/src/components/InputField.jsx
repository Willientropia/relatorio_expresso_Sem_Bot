const InputField = ({ placeholder, value, onChange, type = 'text' }) => {
  return (
    <input
      type={type}
      placeholder={placeholder}
      className="p-2 border rounded w-full"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
};

export default InputField;

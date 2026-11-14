const VARIANTS = {
  primary: 'btn btn-primary',
  secondary: 'btn btn-secondary',
  danger: 'btn btn-danger',
  text: 'btn btn-text',
};

export default function Button({ children, variant = 'primary', type = 'button', className = '', ...props }) {
  return (
    <button type={type} className={`${VARIANTS[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

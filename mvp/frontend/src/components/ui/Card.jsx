import React from 'react';
import { clsx } from 'clsx';

const Card = ({ children, className, ...props }) => {
  return (
    <div 
      className={clsx('bg-white rounded-lg shadow-md border border-gray-200', className)}
      {...props}
    >
      {children}
    </div>
  );
};

const CardHeader = ({ children, className }) => {
  return (
    <div className={clsx('px-6 py-4 border-b border-gray-200', className)}>
      {children}
    </div>
  );
};

const CardContent = ({ children, className }) => {
  return (
    <div className={clsx('px-6 py-4', className)}>
      {children}
    </div>
  );
};

const CardFooter = ({ children, className }) => {
  return (
    <div className={clsx('px-6 py-4 bg-gray-50 rounded-b-lg border-t border-gray-200', className)}>
      {children}
    </div>
  );
};

Card.Header = CardHeader;
Card.Content = CardContent;
Card.Footer = CardFooter;

export default Card;
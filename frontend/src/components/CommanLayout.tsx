import Header from "./Header";
import Footer from "./Footer";

interface Props {
    children: React.ReactNode 
}


const CommanLayout = ({children} : Props) => {
    return(
        <div className="page-wraper">
            <Header design=""/>
                {children}
            <Footer />
        </div>
    )
}
export default CommanLayout;
import { Fragment } from "react"
import Header from "./Header";
import Footer from "./Footer";

interface Props {
    children: React.ReactNode 
}

const MainLayout = ({children} : Props) =>{
    return(
        <Fragment>
            <div className="page-wraper">
                <Header design="style-1 header-transparent"/>
                    {children}
                <Footer />
            </div>
        </Fragment>
    )
}
export default MainLayout;